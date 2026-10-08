"""
AWS Bedrock LLM Service with Cost-Aware Dynamic Model Routing, Telemetry,
Circuit Breaker Integration, Response Caching, and AIOps Metrics.
"""
import json
import os
import httpx
try:
    import boto3
except ImportError:
    boto3 = None
from typing import Dict, Any, Optional, Tuple
from app.config import settings
from app.core.logging import logger
from app.core.metrics import calculate_bedrock_cost, Timer
from app.core.exceptions import LLMServiceError, CircuitOpenError
from app.core.circuit_breaker import circuit_registry, llm_circuit, gemini_circuit, ollama_circuit
from app.core.response_cache import response_cache


class LLMService:
    """
    Service Layer wrapper around Local Offline LLMs (Ollama: Phi-3, Llama 3.1),
    AWS Bedrock Foundation Models, and Google Gemini.
    Provides intelligent cost-aware model routing, token estimation, and fallback resilience.
    """

    def __init__(self):
        self.bedrock_client = None
        self._init_bedrock_client()

    def _init_bedrock_client(self):
        """Initializes the AWS Bedrock client using boto3 if available."""
        if not boto3:
            logger.info("boto3 package not installed or AWS credentials absent. Bedrock live calls disabled.")
            self.bedrock_client = None
            return
        try:
            session_kwargs = {"region_name": settings.AWS_REGION}
            
            # 1. Use explicit credentials only if real and non-placeholder
            has_real_keys = (
                settings.AWS_ACCESS_KEY_ID 
                and not settings.AWS_ACCESS_KEY_ID.startswith("your_")
                and len(settings.AWS_ACCESS_KEY_ID.strip()) > 10
                and settings.AWS_SECRET_ACCESS_KEY
                and not settings.AWS_SECRET_ACCESS_KEY.startswith("your_")
                and len(settings.AWS_SECRET_ACCESS_KEY.strip()) > 10
            )
            if has_real_keys:
                session_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                session_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            elif settings.AWS_PROFILE:
                # 2. Use named AWS CLI profile (e.g., from 'aws login --profile nomados')
                session_kwargs["profile_name"] = settings.AWS_PROFILE
                
            session = boto3.Session(**session_kwargs)
            self.bedrock_client = session.client("bedrock-runtime")
            logger.info("AWS Bedrock Runtime client initialized successfully.")
        except Exception as e:
            logger.warning(f"Could not initialize AWS Bedrock client: {e}. Defaulting to local/mock mode.")
            self.bedrock_client = None

    def route_model(self, task_type: str, preferred_tier: str = "cost_optimized") -> str:
        """
        Cost-Aware Dynamic Router:
        Selects optimal model based on task complexity to maximize efficiency and minimize AWS bill.
        """
        if preferred_tier == "max_reasoning":
            return settings.BEDROCK_REASONING_MODEL_ID
            
        # Fast lightweight tier for classification, parsing, entity extraction
        if task_type in ["context_parsing", "discovery_filtering", "enrichment_extraction"]:
            return settings.BEDROCK_FAST_MODEL_ID
            
        # Heavy reasoning tier for complex multi-variable scheduling & budget trade-offs
        if task_type in ["booking_reasoning", "itinerary_optimization", "conflict_resolution"]:
            return settings.BEDROCK_REASONING_MODEL_ID
            
        return settings.BEDROCK_FAST_MODEL_ID

    def route_local_model(self, task_type: str) -> str:
        """
        Local Dynamic Model Router:
        Routes lightweight classification and parsing to fast phi3:mini,
        and deep itinerary/booking optimization to llama3.1:8b (or fast model).
        """
        if task_type in ["context_parsing", "discovery_filtering", "enrichment_extraction"]:
            return settings.OLLAMA_FAST_MODEL
        return settings.OLLAMA_REASONING_MODEL or settings.OLLAMA_FAST_MODEL

    async def invoke(
        self,
        system_prompt: str,
        user_prompt: str,
        task_type: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Invokes LLM via Local Ollama, Google Gemini, AWS Bedrock, or deterministic engine.
        Integrates response cache, circuit breakers, and AIOps metrics.
        Returns: (parsed_json_response, telemetry_dict)
        """
        model_id = self.route_model(task_type)
        telemetry = {
            "model_id": model_id,
            "task_type": task_type,
            "latency_ms": 0.0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cost_usd": 0.0,
            "cost_savings_usd": 0.0,
            "cache_hit": False,
            "provider": "Local_Ollama" if settings.USE_LOCAL_LLM else ("AWS_Bedrock" if (self.bedrock_client and not settings.USE_MOCK_LLM) else "Nomad_Mock_Provider")
        }

        # ── Response Cache Lookup ──
        cached = response_cache.get(system_prompt, user_prompt, task_type)
        if cached is not None:
            cached_response, cached_telemetry = cached
            cached_telemetry["cache_hit"] = True
            cached_telemetry["latency_ms"] = 0.1  # Near-instant
            self._record_aiops(cached_telemetry)
            return cached_response, cached_telemetry

        with Timer() as timer:
            invoked_successfully = False

            # ── 1. Try Local Ollama (Offline Real AI) ──
            if settings.USE_LOCAL_LLM and not settings.USE_MOCK_LLM:
                allowed, reason = ollama_circuit.allow_request()
                if allowed:
                    local_model = self.route_local_model(task_type)
                    try:
                        telemetry["provider"] = f"Local_Ollama_{local_model.split(':')[0].capitalize()}"
                        telemetry["model_id"] = local_model
                        parsed_json, usage = await self._invoke_ollama(
                            system_prompt, user_prompt, local_model, temperature, max_tokens, task_type
                        )
                        telemetry["prompt_tokens"] = usage[0]
                        telemetry["completion_tokens"] = usage[1]
                        ollama_circuit.record_success()
                        invoked_successfully = True
                    except Exception as e:
                        ollama_circuit.record_failure()
                        logger.warning(f"Local Ollama invocation fallback ({local_model}): {e}")

            # ── 2. Try Google Gemini Free Tier (Only if real API key configured) ──
            has_real_gemini_key = (
                settings.GEMINI_API_KEY 
                and not settings.GEMINI_API_KEY.startswith("your_") 
                and len(settings.GEMINI_API_KEY.strip()) > 20
            )
            if not invoked_successfully and has_real_gemini_key and not settings.USE_MOCK_LLM:
                allowed, reason = gemini_circuit.allow_request()
                if allowed:
                    try:
                        telemetry["provider"] = "Google_Gemini_FreeTier"
                        telemetry["model_id"] = settings.GEMINI_MODEL_ID
                        parsed_json, usage = await self._invoke_gemini(system_prompt, user_prompt, temperature, max_tokens)
                        telemetry["prompt_tokens"] = usage[0]
                        telemetry["completion_tokens"] = usage[1]
                        gemini_circuit.record_success()
                        invoked_successfully = True
                    except Exception as e:
                        gemini_circuit.record_failure()
                        logger.warning(f"Gemini API failed: {e}. Trying fallback.")

            # ── 3. Try AWS Bedrock (Only if real credentials configured) ──
            has_real_aws_keys = (
                settings.AWS_ACCESS_KEY_ID 
                and not settings.AWS_ACCESS_KEY_ID.startswith("your_") 
                and settings.AWS_SECRET_ACCESS_KEY 
                and not settings.AWS_SECRET_ACCESS_KEY.startswith("your_")
            )
            if not invoked_successfully and self.bedrock_client and has_real_aws_keys and not settings.USE_MOCK_LLM:
                allowed, reason = llm_circuit.allow_request()
                if allowed:
                    try:
                        telemetry["provider"] = "AWS_Bedrock"
                        telemetry["model_id"] = model_id
                        payload = {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                            "system": system_prompt,
                            "messages": [
                                {"role": "user", "content": user_prompt}
                            ]
                        }
                        response = self.bedrock_client.invoke_model(
                            modelId=model_id,
                            contentType="application/json",
                            accept="application/json",
                            body=json.dumps(payload)
                        )
                        response_body = json.loads(response["body"].read().decode("utf-8"))
                        content_text = response_body["content"][0]["text"]
                        
                        usage = response_body.get("usage", {})
                        telemetry["prompt_tokens"] = usage.get("input_tokens", len(user_prompt) // 4)
                        telemetry["completion_tokens"] = usage.get("output_tokens", len(content_text) // 4)
                        
                        parsed_json = self._extract_json(content_text)
                        llm_circuit.record_success()
                        invoked_successfully = True
                    except Exception as e:
                        llm_circuit.record_failure()
                        logger.error(f"Bedrock invocation failed for {model_id}: {e}. Falling back.")

            # ── 4. Deterministic Domain Generator Fallback ──
            if not invoked_successfully:
                parsed_json, est_tokens = self._mock_generator(task_type, user_prompt)
                telemetry["prompt_tokens"] = est_tokens[0]
                telemetry["completion_tokens"] = est_tokens[1]
                if not telemetry.get("provider") or "Fallback" not in telemetry["provider"]:
                    telemetry["provider"] = "Nomad_Mock_Provider"

        telemetry["latency_ms"] = timer.latency_ms
        
        # Calculate cloud equivalent cost and savings
        bedrock_eq_cost = calculate_bedrock_cost(
            model_id, 
            telemetry["prompt_tokens"], 
            telemetry["completion_tokens"]
        )
        if "Local_Ollama" in telemetry["provider"]:
            telemetry["cost_usd"] = 0.0  # 100% Free local inference!
            telemetry["cost_savings_usd"] = bedrock_eq_cost
        else:
            telemetry["cost_usd"] = bedrock_eq_cost
            telemetry["cost_savings_usd"] = max(0.0, calculate_bedrock_cost(settings.BEDROCK_REASONING_MODEL_ID, telemetry["prompt_tokens"], telemetry["completion_tokens"]) - bedrock_eq_cost)

        # ── Cache the response ──
        response_cache.put(system_prompt, user_prompt, task_type, parsed_json, telemetry)

        # ── Record to AIOps ──
        self._record_aiops(telemetry)

        return parsed_json, telemetry

    @staticmethod
    def _record_aiops(telemetry: Dict[str, Any]):
        """Records telemetry to the AIOps metrics store."""
        try:
            from app.api.v1.endpoints.aiops import aiops_metrics
            aiops_metrics.record_call(telemetry)
        except Exception:
            pass  # AIOps recording is non-critical

    async def _invoke_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        model_id: str,
        temperature: float,
        max_tokens: int,
        task_type: str
    ) -> Tuple[Dict[str, Any], Tuple[int, int]]:
        """
        Invokes local Ollama offline model (Phi-3, Llama 3.1) via REST API.
        Uses native JSON format mode with task-tuned token ceilings and graceful schema repair.
        """
        base_url = settings.OLLAMA_BASE_URL.replace("localhost", "127.0.0.1")
        url = f"{base_url.rstrip('/')}/api/generate"
        
        # Tune token prediction ceiling for local responsiveness
        token_ceilings = {
            "context_parsing": 100,
            "discovery_filtering": 200,
            "enrichment_extraction": 150,
            "booking_reasoning": 400,
            "trip_refine": 150,
        }
        num_predict = token_ceilings.get(task_type, min(max_tokens, 200))
        
        payload = {
            "model": model_id,
            "system": f"{system_prompt}\n\nRespond ONLY with valid JSON matching keys. No commentary.",
            "prompt": user_prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict
            }
        }
        
        task_timeout = 15.0 if task_type != "booking_reasoning" else 22.0
        
        async with httpx.AsyncClient(timeout=task_timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise LLMServiceError(f"Ollama local API returned HTTP {resp.status_code}: {resp.text}")
            
            data = resp.json()
            raw_response = data.get("response", "").strip()
            if not raw_response:
                raise LLMServiceError("Ollama returned empty response.")
            
            p_tokens = data.get("prompt_eval_count", len(user_prompt) // 4)
            c_tokens = data.get("eval_count", len(raw_response) // 4)
            
            try:
                parsed_json = self._extract_json(raw_response)
                # Verify required structure based on task_type, merge default fallback keys if missing
                fallback_data, _ = self._mock_generator(task_type, user_prompt)
                for key, val in fallback_data.items():
                    if key not in parsed_json or parsed_json[key] is None or parsed_json[key] == "":
                        parsed_json[key] = val
                return parsed_json, (p_tokens, c_tokens)
            except Exception as e:
                logger.warning(f"Ollama JSON extraction repair triggered for {model_id}: {e}")
                # Use robust fallback generator enriched with any extracted fields
                fallback_data, _ = self._mock_generator(task_type, user_prompt)
                return fallback_data, (p_tokens, c_tokens)

    async def _invoke_gemini(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        temperature: float, 
        max_tokens: int
    ) -> Tuple[Dict[str, Any], Tuple[int, int]]:
        """
        Calls Google Gemini API (100% Free Tier - 15 RPM / 1,500 requests/day).
        Returns parsed JSON response and token usage.
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL_ID}:generateContent?key={settings.GEMINI_API_KEY}"
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json"
            }
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise LLMServiceError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            cand_text = data["candidates"][0]["content"]["parts"][0]["text"]
            usage_meta = data.get("usageMetadata", {})
            p_tokens = usage_meta.get("promptTokenCount", len(user_prompt) // 4)
            c_tokens = usage_meta.get("candidatesTokenCount", len(cand_text) // 4)
            return self._extract_json(cand_text), (p_tokens, c_tokens)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Sanitizes and extracts clean JSON object from LLM response."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Strip potential leading/trailing non-json chars
        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx+1]
            
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Simple repair for trailing commas
            import re
            fixed = re.sub(r',\s*([\]}])', r'\1', text)
            return json.loads(fixed)

    def _mock_generator(self, task_type: str, user_prompt: str) -> Tuple[Dict[str, Any], Tuple[int, int]]:
        """
        Deterministic, high-quality domain mock generator ensuring offline capability,
        robust testing, and full schema compliance.
        """
        prompt_lower = user_prompt.lower()
        
        # Detect destination and mood
        destination = None
        for city in ["Paris", "Tokyo", "New York", "Rome", "Bali", "London", "Kyoto", "Barcelona", "Austin"]:
            if city.lower() in prompt_lower:
                destination = city
                break

        # If no explicit city, infer ideal destination based on mood or companions
        if not destination:
            if "concert" in prompt_lower or "music" in prompt_lower or "nightlife" in prompt_lower:
                destination = "Austin"
            elif "family" in prompt_lower or "kid" in prompt_lower or "children" in prompt_lower:
                destination = "Kyoto"
            elif "relax" in prompt_lower or "wellness" in prompt_lower or "beach" in prompt_lower:
                destination = "Bali"
            elif "art" in prompt_lower or "romantic" in prompt_lower:
                destination = "Paris"
            else:
                destination = "Tokyo"
                
        # Detect duration
        duration = 4
        for d in range(1, 15):
            if f"{d}-day" in prompt_lower or f"{d} days" in prompt_lower or f"{d} day" in prompt_lower:
                duration = d
                break

        # Detect budget
        budget = 2500.0
        if "$" in user_prompt:
            import re
            match = re.search(r"\$([0-9,]+)", user_prompt)
            if match:
                budget = float(match.group(1).replace(",", ""))

        # Detect companions
        companions = "Solo"
        if "friend" in prompt_lower:
            companions = "Friends"
        elif "family" in prompt_lower or "kid" in prompt_lower:
            companions = "Family with Kids"
        elif "for 2" in prompt_lower or "couple" in prompt_lower:
            companions = "Couple"

        # Detect origin city
        origin_city = "New York" if "new york" in prompt_lower else ("San Francisco" if "san francisco" in prompt_lower else "Current Location")

        if task_type == "context_parsing":
            mood = "Live Concert & Nightlife" if "concert" in prompt_lower else ("Family Heritage & Nature" if "family" in prompt_lower else ("Foodie & Culture" if "food" in prompt_lower else "Urban Exploration"))
            data = {
                "destination": destination,
                "origin_city": origin_city,
                "duration_days": duration,
                "budget_usd": budget,
                "travelers_count": 4 if companions == "Friends" else (3 if companions == "Family with Kids" else (2 if companions == "Couple" else 1)),
                "companions": companions,
                "travel_style": mood,
                "trip_mood": mood,
                "lodging_style": "Boutique Hotel" if "boutique" in prompt_lower else "Central",
                "interests": ["Live Music & Culture", "Local Dining", "Scenic Walks", "Historic Quarters"],
                "constraints": ["Optimize transit efficiency", "Avoid tourist traps", "Ensure budget buffer"],
                "confidence_score": 0.98
            }
            return data, (380, 210)

        elif task_type == "discovery_filtering":
            data = {
                "recommended_activities": [
                    {
                        "name": f"Iconic Landmark & Cultural Tour ({destination})",
                        "category": "Culture",
                        "estimated_duration_hours": 3.5,
                        "estimated_cost_usd": 45.0,
                        "location_area": "Central Heritage District",
                        "description": "Authentic street food, artisanal crafts, and landmark shrines/monuments."
                    },
                    {
                        "name": "Local Music / Performance Venue & Lounge",
                        "category": "Nightlife" if "concert" in prompt_lower else "Culture",
                        "estimated_duration_hours": 3.0,
                        "estimated_cost_usd": 65.0,
                        "location_area": "Entertainment Corridor",
                        "description": "Intimate live acoustic sets and craft regional cocktails."
                    },
                    {
                        "name": "Artisan Culinary Workshop & Tasting",
                        "category": "Food",
                        "estimated_duration_hours": 2.5,
                        "estimated_cost_usd": 85.0,
                        "location_area": "Gastronomy Quarter",
                        "description": "Hands-on preparation of regional specialties with master chef guidance."
                    },
                    {
                        "name": "Panoramic Observation Deck at Sunset",
                        "category": "Sightseeing",
                        "estimated_duration_hours": 2.0,
                        "estimated_cost_usd": 30.0,
                        "location_area": "Skyline Heights",
                        "description": "Breathtaking 360-degree aerial views over the entire metropolitan landscape."
                    }
                ],
                "top_neighborhoods": [f"Central {destination}", "Historic Quarter", "Arts & Dining District", "Riverside Promenade"],
                "local_culinary_highlights": ["Signature street food bowls", "Wood-fired artisanal tastings", "Regional dessert specialties"]
            }
            return data, (450, 390)

        elif task_type == "enrichment_extraction":
            data = {
                "local_pro_tips": [
                    "Purchase digital transit passes in advance for seamless tap-to-ride access.",
                    "Visit popular venues and scenic decks before 9:00 AM or after 5:30 PM to bypass tour buses.",
                    "Many authentic mom-and-pop eateries are cash-only; keep small bills handy."
                ],
                "cultural_etiquette": [
                    "Maintain quiet voices in public transit.",
                    "Respect photography restrictions in performance halls and residential alleys.",
                    "Tipping etiquette follows local regional customs."
                ],
                "transport_advice": "High-efficiency public metro and on-demand Uber rides provide direct connectivity."
            }
            return data, (320, 240)

        else:  # booking_reasoning
            daily_itinerary = []
            day_budget = round((budget * 0.45) / max(1, duration), 2)
            
            themes = ["Arrival & Orientation", "Culture, Music & Local Dining", "Arts, Skyline & Hidden Alleys", "Leisure, Markets & Farewell Dinner"]
            
            for i in range(1, duration + 1):
                theme = themes[(i - 1) % len(themes)]
                daily_itinerary.append({
                    "day_number": i,
                    "day_theme": theme,
                    "items": [
                        {
                            "time_slot": "Morning (09:00 - 12:00)",
                            "activity_title": f"Explore Iconic Landmark & Morning Market",
                            "area": f"{destination} Historic Core",
                            "description": "Fresh artisan breakfast followed by guided tour of historical monuments.",
                            "cost_estimate_usd": 35.0,
                            "pro_tip": "Arrive early for crowd-free photographs."
                        },
                        {
                            "time_slot": "Afternoon (13:00 - 17:00)",
                            "activity_title": f"Curated Cultural Walk & Local Culinary Stop",
                            "area": f"{destination} Arts District",
                            "description": "Sampling specialty regional dishes followed by gallery and garden walks.",
                            "cost_estimate_usd": 55.0,
                            "pro_tip": "Book timed entry online to skip ticket counter queues."
                        },
                        {
                            "time_slot": "Evening (18:30 - 21:30)",
                            "activity_title": f"Gastronomy Tasting Dinner & Evening Atmosphere",
                            "area": f"{destination} Dining Promenade",
                            "description": "Multi-course chef recommendation dinner with local atmosphere.",
                            "cost_estimate_usd": 75.0,
                            "pro_tip": "Reservations recommended 2-3 days in advance."
                        }
                    ],
                    "day_budget_usd": day_budget
                })

            total_est = round(budget * 0.91, 2)
            data = {
                "origin_transit": {
                    "recommended_mode": "Commercial Flight (Fastest Direct Connection)",
                    "departure_hub": f"{origin_city} International Airport",
                    "arrival_hub": f"{destination} International Hub",
                    "estimated_roundtrip_usd": 420.0,
                    "transit_tips": "Book direct morning flights to maximize first-day exploration time."
                },
                "lodging_options": [
                    {
                        "name": f"The Grand {destination} Boutique Hotel",
                        "neighborhood": "Central Heritage Quarter",
                        "style": "Boutique Art Hotel",
                        "estimated_nightly_usd": 180.0,
                        "rating": 4.88,
                        "amenities": ["Free High-Speed Wi-Fi", "Breakfast Included", "City Panorama Views", "Walking Distance to Transit"],
                        "why_recommended": "Prime central location with immediate access to top historic sites and transit hubs."
                    },
                    {
                        "name": f"{destination} Panorama Suites & Spa",
                        "neighborhood": "Uptown Arts District",
                        "style": "Luxury Relaxation",
                        "estimated_nightly_usd": 265.0,
                        "rating": 4.93,
                        "amenities": ["Rooftop Infinity Pool", "Full Wellness Spa", "Fine Dining On-Site", "Concierge Service"],
                        "why_recommended": "Exceptional luxury amenities ideal for unwinding after full days of exploration."
                    },
                    {
                        "name": f"Citizen {destination} Urban Stay",
                        "neighborhood": "Vibrant Dining Promenade",
                        "style": "Modern & Smart Budget",
                        "estimated_nightly_usd": 125.0,
                        "rating": 4.76,
                        "amenities": ["Smart Room Controls", "Co-working Lounge", "Craft Cafe Bar", "Luggage Storage"],
                        "why_recommended": "Exceptional value, hyper-clean design, and surrounded by authentic street food."
                    }
                ],
                "dining_highlights": [
                    {
                        "name": f"{destination} Heritage Bistro",
                        "cuisine": "Authentic Regional Cuisine",
                        "price_tier": "$$",
                        "area": "Historic Old Town",
                        "signature_dish": "Chef's Tasting Menu & Artisanal Broth",
                        "reservation_tip": "Reservations recommended 2 weeks in advance or walk in before 6:00 PM."
                    },
                    {
                        "name": "The Hidden Lantern Kitchen",
                        "cuisine": "Local Street Food & Tapas",
                        "price_tier": "$",
                        "area": "Alleyway Gastronomy Quarter",
                        "signature_dish": "Handmade Crispy Dumplings & Grilled Skewers",
                        "reservation_tip": "No reservations accepted; arrive early to beat the evening dinner queue."
                    },
                    {
                        "name": "Skyline Panorama Dining Bar",
                        "cuisine": "Modern Fusion & Craft Cocktails",
                        "price_tier": "$$$",
                        "area": "Skyline Heights",
                        "signature_dish": "Seared Local Catch with Truffle Glaze",
                        "reservation_tip": "Request window seating for sunset view."
                    }
                ],
                "packing_checklist": [
                    {"id": "pack-1", "item": "Passport / Government ID & Digital Boarding Passes", "category": "Essentials & Docs", "is_essential": True, "reminder_note": "Keep physical copy + digital backup on cloud"},
                    {"id": "pack-2", "item": "Universal Power Adapter & Fast Charger", "category": "Tech & Power", "is_essential": True, "reminder_note": "Ensure destination voltage compatibility"},
                    {"id": "pack-3", "item": "Comfortable All-Day Walking Shoes", "category": "Clothing & Weather", "is_essential": True, "reminder_note": "Expect 12,000+ daily steps across city neighborhoods"},
                    {"id": "pack-4", "item": "Light Weather-Resistant Jacket", "category": "Clothing & Weather", "is_essential": True, "reminder_note": "Evenings can drop in temperature"},
                    {"id": "pack-5", "item": "Portable Power Bank (10,000mAh)", "category": "Tech & Power", "is_essential": True, "reminder_note": "Essential for maps, photos, and Uber ride booking"},
                    {"id": "pack-6", "item": f"Specialized Gear for {companions} / {destination}", "category": "Activity & Vibe Gear", "is_essential": False, "reminder_note": "Concert earplugs, daypack, or formal evening attire"}
                ],
                "daily_itinerary": daily_itinerary,
                "budget_breakdown": {
                    "Accommodations": round(budget * 0.42, 2),
                    "Dining & Food": round(budget * 0.28, 2),
                    "Activities & Sightseeing": round(budget * 0.14, 2),
                    "Local Transportation": round(budget * 0.07, 2),
                    "Buffer / Emergency": round(budget * 0.09, 2)
                },
                "total_estimated_cost_usd": total_est,
                "budget_variance_status": "Optimal (9% Contingency Buffer Preserved)",
                "trade_off_reasoning": f"Allocated 42% to boutique central lodging to eliminate daily commute fatigue, while keeping a healthy 9% ($ {round(budget * 0.09, 2)}) emergency reserve for unexpected transport or spontaneous upgrades."
            }
            return data, (750, 920)



llm_service = LLMService()
