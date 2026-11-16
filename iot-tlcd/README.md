# iot-tlcd

IOT 액추에이터 팀(박정주·최윤식)의 Claude Code 플러그인입니다.
TLCD 기반 건물 능동제진 연구를 위한 도구와 공유 컨텍스트를 담고 있습니다.

## 들어있는 것

| 스킬 | 하는 일 |
|---|---|
| **weekly-report** | 1주차 발표자료에서 추출한 디자인 시스템 그대로 주간보고서 PPT를 생성합니다. 발표 시간을 주면 발표자 노트까지 만들고 시간을 검증합니다. |
| **tlcd-brief** | 연구 배경·지배방정식·설계 파라미터·선행연구·일정을 제공합니다. 팀원의 Claude가 프로젝트를 즉시 이해합니다. |

## 설치

### 방법 A — 폴더를 직접 복사 (가장 간단, 팀원 추천)

이 `iot-tlcd` 폴더를 통째로 아래 위치에 복사합니다.

```
Windows :  C:\Users\<사용자명>\.claude\skills\iot-tlcd
macOS   :  ~/.claude/skills/iot-tlcd
```

Claude Code를 다시 켜면 `iot-tlcd@skills-dir`로 자동 로드됩니다.
이미 켜져 있다면 `/reload-plugins`를 실행하세요.

확인:

```bash
claude plugin list
```

### 방법 B — GitHub 마켓플레이스 (업데이트 배포에 유리)

이 폴더를 GitHub 저장소로 올린 뒤, 팀원이 실행합니다.

```bash
claude plugin marketplace add <계정>/<저장소>
claude plugin install iot-tlcd
```

이후 수정 사항은 `claude plugin update iot-tlcd`로 받아갑니다.

## 사용법

설치 후 그냥 평소처럼 말하면 됩니다.

```
3주차 주간보고서 만들어줘. 발표는 10분이야.
TLCD 운동방정식 설명해줘
지금 몇 주차고 뭘 해야 하지?
Simulink 모델 검증 순서 알려줘
```

명시적으로 부르려면:

```
/weekly-report
/tlcd-brief
```

## 요구사항

```bash
pip install python-pptx
```

Windows에서 스크립트를 직접 실행할 때는 인코딩을 지정하세요.

```bash
PYTHONIOENCODING=utf-8 python <스크립트>.py
```

## 직접 검증하기

```bash
cd skills/weekly-report/scripts
PYTHONIOENCODING=utf-8 python validate.py "<보고서.ppt>" 17
```

슬라이드 밖 도형, 텍스트 넘침, 표 셀 넘침, 예상 발표 시간을 한 번에 점검합니다.

## 수정할 때

- **디자인을 바꾸지 마세요.** `references/design-tokens.md`의 값은 1주차 원본에서
  추출한 것이라, 바꾸면 주차별 자료의 일관성이 깨집니다.
- **연구 내용이 바뀌면** `skills/tlcd-brief/SKILL.md`를 갱신하세요.
  팀원 전체의 Claude가 이 파일을 기준으로 움직입니다.
- **새 논문을 찾으면** `skills/tlcd-brief/references/papers.md`에 추가하세요.
  단, 2022년 이후 것만.

## 구조

```
iot-tlcd/
├─ .claude-plugin/
│  ├─ plugin.json          플러그인 매니페스트
│  └─ marketplace.json     마켓플레이스 카탈로그 (방법 B용)
├─ skills/
│  ├─ weekly-report/
│  │  ├─ SKILL.md
│  │  ├─ references/design-tokens.md
│  │  └─ scripts/
│  │     ├─ deck.py        PPT 빌더 (색상·좌표·헬퍼)
│  │     └─ validate.py    레이아웃·발표시간 검증기
│  └─ tlcd-brief/
│     ├─ SKILL.md
│     └─ references/papers.md
└─ README.md
```
