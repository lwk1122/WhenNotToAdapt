# Theory Support Scripts

这组脚本的目的不是复现一个完整的在线 SWE-agent 系统，而是围绕 `manuscript_0422.tex` 中的理论对象，构造一套“数据驱动 + 半结构化模拟”的实验支持层。

## 目录

- `build_manifests.py`
  - 统一抽取 `Dataset/` 下 6 套数据的可计算特征，生成轻量 manifest。
- `structural_diagnostics.py`
  - 对应论文里的结构性诊断：
    - verification state compression
    - context atom validity / ranking regret
    - governance-headroom monotonicity
- `certificate_diagnostics.py`
  - 对应论文里的 certificate / recovery / amplification 相关诊断。
- `controller_benchmark.py`
  - 基于数据代理量的半结构化 controller benchmark，用于比较 Oracle-SRC、RSRC、SE-MPC 和多种 baseline。
- `run_all.py`
  - 串联运行上述脚本。

## 推荐运行顺序

```powershell
.venv_dl\Scripts\python scripts\theory_support\build_manifests.py
.venv_dl\Scripts\python scripts\theory_support\structural_diagnostics.py
.venv_dl\Scripts\python scripts\theory_support\certificate_diagnostics.py
.venv_dl\Scripts\python scripts\theory_support\controller_benchmark.py
```

或者一次性运行：

```powershell
.venv_dl\Scripts\python scripts\theory_support\run_all.py
```

## 输出目录

默认输出到：

- `results/theory_support/manifests/`
- `results/theory_support/diagnostics/`
- `results/theory_support/benchmark/`

## 注意

1. 这些脚本是“支撑理论”的实验层，不是生产级 benchmark harness。
2. `controller_benchmark.py` 是数据代理量驱动的半结构化模拟，不直接执行 repo、容器和真实测试。
3. `structural_diagnostics.py` 与 `certificate_diagnostics.py` 优先服务于论文中的结构性、稳定性与证书主张。
