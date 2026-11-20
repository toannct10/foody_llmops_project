# Production model selection

Versioned decision: `config/model_selection.json` selects **Qwen2.5-3B-Instruct**.
The evidence is the complete run `20261107T022914Z-bccf46ea` on
`foody_text_to_sql_12_v1` (SHA256
`3b995a92f053366898e65cb5eb3f7e01597ce6f6da18adf3a65e021586c69cfc`).
Qwen produced 10/10 correct model results, 100% structured-output validity
and 1,086 ms mean generation latency. Llama produced 5/10 correct model
results and DeepSeek 0/10. Application fallback and pre-model unsafe policy
refusals are reported separately in the benchmark comparison.

This small, project-specific acceptance set supports the project choice; it
is not a general model ranking. Qwen remains the existing production model.
No fine-tuning, production switch or new Docker model service occurred.
