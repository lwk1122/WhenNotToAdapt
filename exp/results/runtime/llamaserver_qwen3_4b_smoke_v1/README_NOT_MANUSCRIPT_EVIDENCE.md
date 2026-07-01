This directory records an exploratory compatibility smoke test with
Qwen3-4B-Q4_K_M.gguf served by llama.cpp while reasoning output was enabled.
The model placed its response in the reasoning stream, so the existing JSON
choice parser could not recover task choices. These files are kept only as a
protocol record and are not used as manuscript evidence.
