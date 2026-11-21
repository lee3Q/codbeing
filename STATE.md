# STATE

- 목표: 확인된 Codbeing 보안 finding을 최소 수정하고 검증 가능한 커밋과 감사 산출물을 남긴다.
- 금지 조건: main 직접 수정·강제 덮어쓰기·다른 작업 트리 삭제·비밀값 기록·GitHub push/PR 생성 금지.
- 확인된 사실: F-002는 config 신규 저장이 umask 022에서 0644가 되는 문제였다. C-02는 legacy public receipt가 현재 verifier의 observed attempt 계약을 위반했다.
- 적용: config는 same-directory temp + fchmod 0600 + fsync + os.replace로 저장한다. public ledger는 EvidenceLedger.run()으로 재생성하고 expected head를 갱신했다. built-in open report fix와 기존 변경을 보존했다.
- 검증: 317 passed, 31 subtests. verify_installation PASS. reproduce_synthetic_cycle PASS. public ledger expected head 96a83068d6ee42fe2f65b323830de46e4fde29008217bfeb5501f92707ed5d3b PASS with current_status.public_cycle=PASS.
- 미검증: Python 3.10–3.12 직접 실행, 외부 provider 호출, 장시간 fault injection, cross-device filesystem.
- 완료: 1e1ce79 변경을 보존한 공개 ledger fixture 보수 작업이 진행 중이며, 다음 커밋에서 완료한다.
