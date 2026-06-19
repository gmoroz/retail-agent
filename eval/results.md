# Retail Agent A/B Eval Results

Generated at: 2026-06-18T19:19:03Z
Ranking rule: correctness DESC, report quality band DESC (0.05 LLM-judge noise floor), mean cost ASC, mean latency ASC, model ASC
Winner / pinned default: deepseek/deepseek-v4-flash

| Model | Questions | Correctness | Quality | Total cost | Mean cost | Mean latency | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| deepseek/deepseek-v4-flash | 20 | 0.800 | 0.633 | 0.006836 | 0.000342 | 24.67s | 41875 |
| z-ai/glm-5.2 | 20 | 0.800 | 0.635 | 0.134470 | 0.006724 | 44.87s | 46938 |
| qwen/qwen3.7-plus | 20 | 0.800 | 0.620 | 0.117913 | 0.005896 | 97.48s | 110153 |
| moonshotai/kimi-k2 | 20 | 0.550 | 0.585 | 0.025105 | 0.001255 | 29.61s | 29312 |

## Case Results

| Model | Question | Outcome | Correct | Quality | Cost | Latency | Error |
|---|---|---|---:|---:|---:|---:|---|
| deepseek/deepseek-v4-flash | holdout_001 | ok | 1 | 1.000 | 0.000283 | 30.32s |  |
| deepseek/deepseek-v4-flash | holdout_002 | ok | 1 | 0.500 | 0.000346 | 32.18s |  |
| deepseek/deepseek-v4-flash | holdout_003 | ok | 1 | 0.500 | 0.000302 | 28.24s |  |
| deepseek/deepseek-v4-flash | holdout_004 | ok | 1 | 0.800 | 0.000363 | 35.16s |  |
| deepseek/deepseek-v4-flash | holdout_005 | ok | 1 | 1.000 | 0.000170 | 23.02s |  |
| deepseek/deepseek-v4-flash | holdout_006 | ok | 1 | 1.000 | 0.000195 | 21.68s |  |
| deepseek/deepseek-v4-flash | holdout_007 | ok | 1 | 1.000 | 0.000137 | 20.04s |  |
| deepseek/deepseek-v4-flash | holdout_008 | ok | 1 | 1.000 | 0.000214 | 22.03s |  |
| deepseek/deepseek-v4-flash | holdout_009 | ok | 1 | 1.000 | 0.000275 | 25.19s |  |
| deepseek/deepseek-v4-flash | holdout_010 | ok | 1 | 1.000 | 0.000403 | 20.72s |  |
| deepseek/deepseek-v4-flash | holdout_011 | ok | 1 | 1.000 | 0.000308 | 19.87s |  |
| deepseek/deepseek-v4-flash | holdout_012 | ok | 1 | 0.000 | 0.000361 | 24.92s |  |
| deepseek/deepseek-v4-flash | holdout_013 | ok | 1 | 1.000 | 0.000363 | 23.01s |  |
| deepseek/deepseek-v4-flash | holdout_014 | ok | 1 | 0.500 | 0.000407 | 23.68s |  |
| deepseek/deepseek-v4-flash | holdout_015 | ok | 1 | 0.000 | 0.000737 | 29.72s |  |
| deepseek/deepseek-v4-flash | holdout_016 | ok | 0 | 0.000 | 0.000453 | 22.91s |  |
| deepseek/deepseek-v4-flash | holdout_017 | ok | 1 | 0.900 | 0.000438 | 22.96s |  |
| deepseek/deepseek-v4-flash | holdout_018 | ok | 0 | 0.000 | 0.000342 | 23.05s |  |
| deepseek/deepseek-v4-flash | holdout_019 | ok | 0 | 0.450 | 0.000353 | 23.01s |  |
| deepseek/deepseek-v4-flash | holdout_020 | ok | 0 | 0.000 | 0.000387 | 21.77s |  |
| qwen/qwen3.7-plus | holdout_001 | ok | 1 | 0.500 | 0.007300 | 127.73s |  |
| qwen/qwen3.7-plus | holdout_002 | ok | 1 | 1.000 | 0.006390 | 101.82s |  |
| qwen/qwen3.7-plus | holdout_003 | ok | 1 | 0.500 | 0.005865 | 95.89s |  |
| qwen/qwen3.7-plus | holdout_004 | ok | 1 | 0.500 | 0.006563 | 104.25s |  |
| qwen/qwen3.7-plus | holdout_005 | ok | 1 | 1.000 | 0.005029 | 84.26s |  |
| qwen/qwen3.7-plus | holdout_006 | ok | 1 | 1.000 | 0.003815 | 67.24s |  |
| qwen/qwen3.7-plus | holdout_007 | ok | 1 | 1.000 | 0.004636 | 80.76s |  |
| qwen/qwen3.7-plus | holdout_008 | ok | 1 | 1.000 | 0.003778 | 71.98s |  |
| qwen/qwen3.7-plus | holdout_009 | ok | 1 | 1.000 | 0.005204 | 87.56s |  |
| qwen/qwen3.7-plus | holdout_010 | ok | 1 | 0.800 | 0.007660 | 123.65s |  |
| qwen/qwen3.7-plus | holdout_011 | ok | 1 | 0.900 | 0.004804 | 86.42s |  |
| qwen/qwen3.7-plus | holdout_012 | ok | 1 | 0.000 | 0.007276 | 114.91s |  |
| qwen/qwen3.7-plus | holdout_013 | ok | 0 | 0.500 | 0.005857 | 95.42s |  |
| qwen/qwen3.7-plus | holdout_014 | ok | 1 | 0.500 | 0.005725 | 96.80s |  |
| qwen/qwen3.7-plus | holdout_015 | ok | 1 | 0.000 | 0.007009 | 108.65s |  |
| qwen/qwen3.7-plus | holdout_016 | ok | 1 | 1.000 | 0.005566 | 90.19s |  |
| qwen/qwen3.7-plus | holdout_017 | ok | 1 | 0.700 | 0.006543 | 105.54s |  |
| qwen/qwen3.7-plus | holdout_018 | no_data | 0 | 0.000 | 0.004175 | 63.58s | No matching data was returned for this question. |
| qwen/qwen3.7-plus | holdout_019 | ok | 0 | 0.500 | 0.006662 | 111.88s |  |
| qwen/qwen3.7-plus | holdout_020 | ok | 0 | 0.000 | 0.008056 | 131.12s |  |
| moonshotai/kimi-k2 | holdout_001 | ok | 0 | 0.500 | 0.001266 | 31.07s |  |
| moonshotai/kimi-k2 | holdout_002 | ok | 1 | 0.700 | 0.001368 | 33.20s |  |
| moonshotai/kimi-k2 | holdout_003 | ok | 1 | 0.800 | 0.001169 | 30.11s |  |
| moonshotai/kimi-k2 | holdout_004 | ok | 0 | 0.000 | 0.001508 | 30.59s |  |
| moonshotai/kimi-k2 | holdout_005 | ok | 1 | 1.000 | 0.000962 | 23.56s |  |
| moonshotai/kimi-k2 | holdout_006 | ok | 1 | 1.000 | 0.000793 | 23.29s |  |
| moonshotai/kimi-k2 | holdout_007 | ok | 1 | 1.000 | 0.000702 | 20.68s |  |
| moonshotai/kimi-k2 | holdout_008 | ok | 1 | 1.000 | 0.000688 | 19.14s |  |
| moonshotai/kimi-k2 | holdout_009 | ok | 1 | 1.000 | 0.001188 | 28.32s |  |
| moonshotai/kimi-k2 | holdout_010 | ok | 1 | 1.000 | 0.001956 | 32.13s |  |
| moonshotai/kimi-k2 | holdout_011 | ok | 0 | 0.500 | 0.000997 | 25.56s |  |
| moonshotai/kimi-k2 | holdout_012 | ok | 1 | 0.000 | 0.001184 | 25.26s |  |
| moonshotai/kimi-k2 | holdout_013 | ok | 0 | 0.500 | 0.001264 | 29.37s |  |
| moonshotai/kimi-k2 | holdout_014 | ok | 1 | 0.900 | 0.001143 | 31.70s |  |
| moonshotai/kimi-k2 | holdout_015 | ok | 0 | 0.000 | 0.001778 | 30.73s |  |
| moonshotai/kimi-k2 | holdout_016 | ok | 0 | 0.000 | 0.001369 | 33.77s |  |
| moonshotai/kimi-k2 | holdout_017 | ok | 1 | 0.800 | 0.001423 | 38.53s |  |
| moonshotai/kimi-k2 | holdout_018 | ok | 0 | 0.000 | 0.001707 | 36.08s |  |
| moonshotai/kimi-k2 | holdout_019 | ok | 0 | 1.000 | 0.001175 | 32.35s |  |
| moonshotai/kimi-k2 | holdout_020 | ok | 0 | 0.000 | 0.001465 | 36.78s |  |
| z-ai/glm-5.2 | holdout_001 | ok | 1 | 0.200 | 0.006128 | 31.32s |  |
| z-ai/glm-5.2 | holdout_002 | ok | 1 | 0.800 | 0.007420 | 46.17s |  |
| z-ai/glm-5.2 | holdout_003 | ok | 1 | 1.000 | 0.009717 | 88.61s |  |
| z-ai/glm-5.2 | holdout_004 | ok | 1 | 1.000 | 0.009201 | 50.80s |  |
| z-ai/glm-5.2 | holdout_005 | ok | 1 | 0.500 | 0.003019 | 32.20s |  |
| z-ai/glm-5.2 | holdout_006 | ok | 1 | 1.000 | 0.002449 | 32.84s |  |
| z-ai/glm-5.2 | holdout_007 | ok | 1 | 1.000 | 0.004108 | 36.71s |  |
| z-ai/glm-5.2 | holdout_008 | ok | 1 | 1.000 | 0.004135 | 25.71s |  |
| z-ai/glm-5.2 | holdout_009 | ok | 1 | 0.500 | 0.007330 | 40.03s |  |
| z-ai/glm-5.2 | holdout_010 | ok | 1 | 0.700 | 0.009720 | 43.91s |  |
| z-ai/glm-5.2 | holdout_011 | ok | 1 | 1.000 | 0.002720 | 19.63s |  |
| z-ai/glm-5.2 | holdout_012 | ok | 1 | 0.000 | 0.009306 | 65.17s |  |
| z-ai/glm-5.2 | holdout_013 | ok | 0 | 0.600 | 0.005486 | 41.75s |  |
| z-ai/glm-5.2 | holdout_014 | ok | 1 | 0.900 | 0.006748 | 57.00s |  |
| z-ai/glm-5.2 | holdout_015 | ok | 1 | 0.000 | 0.005240 | 38.46s |  |
| z-ai/glm-5.2 | holdout_016 | ok | 1 | 0.700 | 0.007077 | 49.50s |  |
| z-ai/glm-5.2 | holdout_017 | ok | 1 | 0.800 | 0.008985 | 49.71s |  |
| z-ai/glm-5.2 | holdout_018 | ok | 0 | 0.000 | 0.008862 | 52.33s |  |
| z-ai/glm-5.2 | holdout_019 | ok | 0 | 1.000 | 0.006528 | 44.03s |  |
| z-ai/glm-5.2 | holdout_020 | ok | 0 | 0.000 | 0.010291 | 51.47s |  |
