# Local resource and cost control

`src/monitoring/cost.py` reads only LLMOps generation events. It reports calls, input/output/total tokens, average tokens/call, generation wall time, and daily/ISO-weekly/model/task breakdowns. Request rows are excluded to avoid double-counting. CPU/GPU seconds and peak RAM/VRAM are **not** inferred from tokens. The System Monitor separately shows current visible CPU/memory and GPU/VRAM only if `nvidia-smi` is available.

Monetary estimates default to `NOT_CONFIGURED`. To opt in, set `COST_TRACKING_ENABLED=true`, `LOCAL_INFERENCE_DEVICE=cpu` or `gpu`, and the matching `LOCAL_CPU_COST_PER_HOUR` or `LOCAL_GPU_COST_PER_HOUR`. The formula is **generation wall seconds × configured hourly device rate / 3600**. This is an `ESTIMATE` of dedicated device time, not token billing, cloud spend, electricity measurement or an accounting total. State the currency in operator documentation; the application does not assume one. Invalid/missing rate keeps cost unavailable.

`SNOWFLAKE_CREDIT_PRICE` and `AWS_ESTIMATE_MODE` are reserved configuration inputs. They do not create spend values without measured credits/usage. AWS and Snowflake actual cost remain `NOT_CONFIGURED` because live credentials are absent. Keep rates outside Git when deployment-specific.
