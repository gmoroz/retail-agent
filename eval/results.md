# Retail Agent A/B Eval Results

Generated at: 2026-06-19T10:37:52Z
Ranking rule: correctness DESC, report quality band DESC (0.05 LLM-judge noise floor), mean cost ASC, mean latency ASC, model ASC
Accuracy leader: qwen/qwen3.7-plus (correctness 0.750)
Pinned default: deepseek/deepseek-v4-flash -- most accurate model within the interactive latency SLA (<= 45s); qwen/qwen3.7-plus excluded as default (mean latency 95.3s exceeds the budget).

| Model | Questions | Correctness | Quality | Total cost | Mean cost | Mean latency | Tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen/qwen3.7-plus | 20 | 0.750 | 0.670 | 0.116534 | 0.005827 | 95.34s | 109957 |
| deepseek/deepseek-v4-flash | 20 | 0.700 | 0.635 | 0.006796 | 0.000340 | 21.64s | 44786 |
| z-ai/glm-5.2 | 20 | 0.650 | 0.605 | 0.117568 | 0.005878 | 27.77s | 43180 |
| moonshotai/kimi-k2 | 20 | 0.450 | 0.532 | 0.024463 | 0.001223 | 24.16s | 29250 |

## Case Results

| Model | Question | Outcome | Correct | Quality | Cost | Latency | Error |
|---|---|---|---:|---:|---:|---:|---|
| deepseek/deepseek-v4-flash | holdout_001 | ok | 1 | 1.000 | 0.000403 | 22.70s |  |
| deepseek/deepseek-v4-flash | holdout_002 | ok | 1 | 1.000 | 0.000355 | 18.50s |  |
| deepseek/deepseek-v4-flash | holdout_003 | ok | 1 | 0.700 | 0.000386 | 20.23s |  |
| deepseek/deepseek-v4-flash | holdout_004 | ok | 0 | 0.000 | 0.000738 | 25.88s |  |
| deepseek/deepseek-v4-flash | holdout_005 | ok | 1 | 1.000 | 0.000389 | 17.51s |  |
| deepseek/deepseek-v4-flash | holdout_006 | ok | 1 | 1.000 | 0.000280 | 15.50s |  |
| deepseek/deepseek-v4-flash | holdout_007 | ok | 1 | 1.000 | 0.000265 | 13.77s |  |
| deepseek/deepseek-v4-flash | holdout_008 | ok | 1 | 1.000 | 0.000258 | 14.02s |  |
| deepseek/deepseek-v4-flash | holdout_009 | ok | 1 | 1.000 | 0.000365 | 16.83s |  |
| deepseek/deepseek-v4-flash | holdout_010 | ok | 1 | 1.000 | 0.000258 | 21.22s |  |
| deepseek/deepseek-v4-flash | holdout_011 | ok | 1 | 1.000 | 0.000177 | 16.71s |  |
| deepseek/deepseek-v4-flash | holdout_012 | ok | 1 | 0.000 | 0.000331 | 28.52s |  |
| deepseek/deepseek-v4-flash | holdout_013 | ok | 0 | 0.500 | 0.000234 | 22.31s |  |
| deepseek/deepseek-v4-flash | holdout_014 | ok | 1 | 0.500 | 0.000242 | 22.16s |  |
| deepseek/deepseek-v4-flash | holdout_015 | ok | 1 | 0.000 | 0.000543 | 34.12s |  |
| deepseek/deepseek-v4-flash | holdout_016 | ok | 0 | 0.000 | 0.000352 | 26.91s |  |
| deepseek/deepseek-v4-flash | holdout_017 | ok | 1 | 1.000 | 0.000284 | 24.14s |  |
| deepseek/deepseek-v4-flash | holdout_018 | ok | 0 | 0.000 | 0.000393 | 28.15s |  |
| deepseek/deepseek-v4-flash | holdout_019 | ok | 0 | 1.000 | 0.000259 | 21.44s |  |
| deepseek/deepseek-v4-flash | holdout_020 | ok | 0 | 0.000 | 0.000281 | 22.24s |  |
| qwen/qwen3.7-plus | holdout_001 | ok | 1 | 0.500 | 0.005419 | 160.63s |  |
| qwen/qwen3.7-plus | holdout_002 | ok | 1 | 1.000 | 0.005436 | 85.23s |  |
| qwen/qwen3.7-plus | holdout_003 | ok | 1 | 1.000 | 0.009235 | 139.58s |  |
| qwen/qwen3.7-plus | holdout_004 | ok | 1 | 0.500 | 0.005630 | 90.54s |  |
| qwen/qwen3.7-plus | holdout_005 | ok | 1 | 1.000 | 0.005136 | 81.81s |  |
| qwen/qwen3.7-plus | holdout_006 | ok | 1 | 1.000 | 0.003837 | 62.78s |  |
| qwen/qwen3.7-plus | holdout_007 | ok | 1 | 1.000 | 0.004668 | 75.39s |  |
| qwen/qwen3.7-plus | holdout_008 | ok | 1 | 1.000 | 0.003115 | 51.85s |  |
| qwen/qwen3.7-plus | holdout_009 | ok | 1 | 1.000 | 0.007082 | 108.26s |  |
| qwen/qwen3.7-plus | holdout_010 | ok | 1 | 0.900 | 0.004728 | 76.79s |  |
| qwen/qwen3.7-plus | holdout_011 | ok | 1 | 1.000 | 0.005322 | 83.81s |  |
| qwen/qwen3.7-plus | holdout_012 | ok | 1 | 0.500 | 0.006319 | 97.47s |  |
| qwen/qwen3.7-plus | holdout_013 | ok | 0 | 0.500 | 0.005578 | 88.37s |  |
| qwen/qwen3.7-plus | holdout_014 | ok | 1 | 0.500 | 0.006294 | 96.83s |  |
| qwen/qwen3.7-plus | holdout_015 | ok | 1 | 0.000 | 0.006873 | 104.12s |  |
| qwen/qwen3.7-plus | holdout_016 | ok | 1 | 1.000 | 0.006245 | 96.54s |  |
| qwen/qwen3.7-plus | holdout_017 | ok | 0 | 0.000 | 0.007582 | 117.51s |  |
| qwen/qwen3.7-plus | holdout_018 | ok | 0 | 0.000 | 0.005643 | 90.50s |  |
| qwen/qwen3.7-plus | holdout_019 | ok | 0 | 1.000 | 0.004966 | 83.31s |  |
| qwen/qwen3.7-plus | holdout_020 | ok | 0 | 0.000 | 0.007426 | 115.43s |  |
| moonshotai/kimi-k2 | holdout_001 | ok | 1 | 0.500 | 0.001146 | 24.62s |  |
| moonshotai/kimi-k2 | holdout_002 | ok | 1 | 0.800 | 0.001174 | 27.15s |  |
| moonshotai/kimi-k2 | holdout_003 | ok | 1 | 1.000 | 0.001964 | 29.13s |  |
| moonshotai/kimi-k2 | holdout_004 | ok | 0 | 0.000 | 0.001295 | 23.70s |  |
| moonshotai/kimi-k2 | holdout_005 | ok | 1 | 1.000 | 0.001054 | 23.20s |  |
| moonshotai/kimi-k2 | holdout_006 | ok | 1 | 0.800 | 0.000841 | 21.03s |  |
| moonshotai/kimi-k2 | holdout_007 | ok | 1 | 1.000 | 0.000721 | 17.27s |  |
| moonshotai/kimi-k2 | holdout_008 | ok | 1 | 1.000 | 0.000826 | 16.59s |  |
| moonshotai/kimi-k2 | holdout_009 | ok | 0 | 1.000 | 0.001216 | 28.02s |  |
| moonshotai/kimi-k2 | holdout_010 | ok | 1 | 0.850 | 0.001224 | 23.38s |  |
| moonshotai/kimi-k2 | holdout_011 | ok | 0 | 0.500 | 0.001211 | 22.69s |  |
| moonshotai/kimi-k2 | holdout_012 | ok | 1 | 0.700 | 0.001220 | 24.16s |  |
| moonshotai/kimi-k2 | holdout_013 | ok | 0 | 0.500 | 0.001298 | 28.73s |  |
| moonshotai/kimi-k2 | holdout_014 | ok | 0 | 0.500 | 0.001150 | 24.14s |  |
| moonshotai/kimi-k2 | holdout_015 | ok | 0 | 0.000 | 0.001888 | 25.46s |  |
| moonshotai/kimi-k2 | holdout_016 | ok | 0 | 0.000 | 0.001303 | 24.55s |  |
| moonshotai/kimi-k2 | holdout_017 | ok | 0 | 0.000 | 0.001148 | 24.81s |  |
| moonshotai/kimi-k2 | holdout_018 | ok | 0 | 0.000 | 0.001090 | 23.02s |  |
| moonshotai/kimi-k2 | holdout_019 | ok | 0 | 0.500 | 0.001260 | 23.45s |  |
| moonshotai/kimi-k2 | holdout_020 | ok | 0 | 0.000 | 0.001434 | 28.15s |  |
| z-ai/glm-5.2 | holdout_001 | ok | 1 | 0.500 | 0.005945 | 21.10s |  |
| z-ai/glm-5.2 | holdout_002 | ok | 1 | 0.800 | 0.009036 | 37.42s |  |
| z-ai/glm-5.2 | holdout_003 | ok | 1 | 0.500 | 0.007158 | 28.55s |  |
| z-ai/glm-5.2 | holdout_004 | ok | 0 | 0.000 | 0.010264 | 46.34s |  |
| z-ai/glm-5.2 | holdout_005 | ok | 1 | 1.000 | 0.003581 | 21.78s |  |
| z-ai/glm-5.2 | holdout_006 | ok | 1 | 1.000 | 0.004257 | 37.29s |  |
| z-ai/glm-5.2 | holdout_007 | ok | 1 | 1.000 | 0.005221 | 21.36s |  |
| z-ai/glm-5.2 | holdout_008 | ok | 1 | 1.000 | 0.002739 | 20.68s |  |
| z-ai/glm-5.2 | holdout_009 | ok | 0 | 0.800 | 0.005319 | 33.20s |  |
| z-ai/glm-5.2 | holdout_010 | ok | 1 | 0.900 | 0.005537 | 24.68s |  |
| z-ai/glm-5.2 | holdout_011 | ok | 1 | 1.000 | 0.006085 | 21.13s |  |
| z-ai/glm-5.2 | holdout_012 | ok | 1 | 0.500 | 0.006144 | 25.80s |  |
| z-ai/glm-5.2 | holdout_013 | ok | 0 | 0.400 | 0.004697 | 21.01s |  |
| z-ai/glm-5.2 | holdout_014 | ok | 1 | 0.500 | 0.005725 | 21.04s |  |
| z-ai/glm-5.2 | holdout_015 | ok | 1 | 0.000 | 0.005819 | 23.31s |  |
| z-ai/glm-5.2 | holdout_016 | ok | 1 | 1.000 | 0.007976 | 34.41s |  |
| z-ai/glm-5.2 | holdout_017 | ok | 0 | 0.700 | 0.006363 | 33.09s |  |
| z-ai/glm-5.2 | holdout_018 | no_data | 0 | 0.000 | 0.003375 | 9.11s | No matching data was returned for this question. |
| z-ai/glm-5.2 | holdout_019 | ok | 0 | 0.500 | 0.006782 | 44.19s |  |
| z-ai/glm-5.2 | holdout_020 | ok | 0 | 0.000 | 0.005546 | 29.80s |  |
