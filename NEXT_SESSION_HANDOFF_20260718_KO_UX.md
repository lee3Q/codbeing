# codbeing Next Session Handoff - 2026-07-18 Korean Lab UX

## Read This First

This handoff records the outcome of the overnight OZO/codbeing Korean UX run.
The product changes are useful and locally verified, but the outer Ouroboros
harness did not PASS.

## Outcome

The `cb` / `python3 -m codbeing` no-args entrance is now Korean-first.

Observed launcher smoke:

```text
코드빙 연구실 (codbeing Lab)
내 기록을 이 기기 안에서 정리하고 살펴보는 개인 연구실입니다.
기본값은 로컬 전용입니다. API 키 없이도 기록과 분석을 사용할 수 있습니다.
외부 모델(GLM 등)은 직접 선택하고 키가 준비된 경우에만 사용합니다.
이 화면은 비밀값, API 키, 원문 개인 기록을 출력하지 않습니다.

처음 할 일:
  1. 노무사 예시로 시작하기 (Nomusa 데모)
  2. 내 결정 기록하기 (기록/캡처)
  3. 저장된 기록 분석 보기
  4. 모델·개인정보 상태 확인
```

The UX is not final, but it is no longer English-first command help.

## Verified Now

Commands run from `/Users/sanggyulee/codbeing` after the overnight recovery:

```bash
python3 -m unittest discover -s tests -v
python3 -m pytest -q
printf 'q\n' | python3 -m codbeing
```

Results:

- `python3 -m unittest discover -s tests -v` -> `Ran 60 tests ... OK`
- `python3 -m pytest -q` -> `78 passed`
- no-args smoke exits and shows Korean-first Lab copy, local-first privacy copy,
  four first actions, and legacy command guidance.

## Files Touched During The UX Work

Observed recently modified project files:

- `codbeing/__main__.py`
- `tests/test_cb_lab_launcher.py`
- `tests/test_cli_validation.py`
- `private-traces/submitted-material.json`
- generated reports under `private-reports/academic-nomusa-runtime-analysis-*.md`

Do not assume the generated private reports are product source.

## What Actually Improved

- Korean-first no-args Lab entrance.
- Local-first privacy and model boundary copy in Korean.
- Four non-developer first actions:
  - Nomusa demo
  - record/capture a decision
  - view saved analysis
  - model/privacy status
- Legacy command guidance remains visible for power users.
- Tests now cover the Korean-first no-args launcher and privacy/model boundary.

## What Did Not Complete

The outer harness did not reach PASS.

Run dir:

```text
~/.ouroboros/harness/runs/codbeing-success-loop-20260718-034612
```

At recovery:

- Summary status: `retrying`
- Attempts: `662`
- Failure signatures:
  - `stale_no_progress`: 1
  - `exit_1`: 661

Latest failure cause was not a codbeing UX assertion. The local `ooo`
executable imported through `/Users/sanggyulee/ouroboros-zcode/.venv` Python
3.14 and failed during pydantic annotation evaluation:

```text
TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'
Unable to evaluate type annotation 'str'.
```

Judgment: the product change landed, but the overnight harness result is an
Ouroboros/runtime environment failure, not a formal successful `ooo auto`
completion.

## Related OZO Records

- `~/ouroboros-zcode-meta/OZO_POWER_RECOVERY_20260718.md`
- `~/ouroboros-zcode-meta/OZO_PROCESS_HYGIENE_20260718.md`
- `~/ouroboros-zcode-meta/SESSION_DECISIONS.md` session 93
- `~/.ouroboros/harness/runs/codbeing-success-loop-20260718-034612/summary.json`

## Next Safe Steps

1. Inspect `codbeing/__main__.py` and the launcher tests to decide whether the
   Korean-first UX should be treated as accepted product state.
2. Do not resume the same unbounded codbeing harness until `ooo` is forced to a
   Python 3.10/3.13-compatible environment or the Python 3.14/pydantic mismatch
   is fixed.
3. If continuing UX polish, focus on replacing remaining mixed English in the
   state line and making the first-action loop feel less CLI-like.
4. If formalizing with Ouroboros, use a bounded retry cap and fail-fast on
   import/runtime errors before retrying.

