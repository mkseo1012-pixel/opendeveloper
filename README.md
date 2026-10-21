# ◈ OpenDeveloper

**Observe. Reimagine. Build.** 공개 웹사이트에서 기능을 분석하고, 독창적인 기능과 다른 UI를 계획한 뒤 사용자의 승인을 받아 HTML·ZIP으로 만드는 로컬 오픈소스 개발 에이전트입니다.

Python 3.11+ · CLI + localhost · 런타임 외부 패키지 없음 · MIT

## 사용 흐름

1. API URL, 모델 ID와 API 키 또는 OAuth를 연결합니다.
2. 공개 HTTPS 웹사이트 URL과 원하는 기능을 입력합니다.
3. 관찰한 기능, 최소 3개 차별화 기능, UI 스타일, 검증 기준과 메모를 포함한 계획서를 읽습니다.
4. 채팅 입력창에서 수정을 요청하거나 **이 계획 승인**을 누릅니다.
5. **승인한 계획으로 개발**을 선택합니다. 에이전트가 구현 → 정적 검토 → 필요 시 한 번 수정 → 재검토를 진행합니다.
6. 채팅창에서 **index.html** 또는 **project.zip**을 다운로드합니다. ZIP에는 계획·검토·개발 메모가 포함됩니다.

계획 수정 시 승인이 무효화됩니다. 서버에서도 승인 상태와 계획 해시를 검사하므로 UI를 건너뛰어도 승인 전 생성할 수 없습니다.

## Windows 설치: CMD

GitHub의 Code → Download ZIP으로 내려받아 압축을 푼 폴더에서 실행합니다. Python 설치 시 Python Launcher를 포함하세요.

```bat
install.cmd
.venv\Scripts\opendeveloper.exe serve
```

## Windows 설치: PowerShell

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
.\.venv\Scripts\opendeveloper.exe serve
```

`http://127.0.0.1:8765`에서 열립니다. 설치는 가상환경을 만들고 현재 소스를 설치하며, 실행 정책을 영구 변경하거나 관리자 권한을 요구하지 않습니다. 설치 시 pip 빌드 도구 다운로드를 위한 인터넷 연결이 필요할 수 있습니다.

## macOS / Linux

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/opendeveloper serve
```

설치 없이 소스 폴더에서 `python -m opendeveloper serve`로 실행할 수도 있습니다.

## API 연결

localhost의 **연결 설정**에서 Chat Completions 호환 API의 Base URL(예: 공급자의 `/v1` URL), 모델 ID, 키를 입력합니다. Base URL에 `/chat/completions`를 붙여 JSON 생성 요청을 보냅니다. 모델은 충분한 출력 길이와 JSON 객체 출력을 지원해야 합니다. 특정 공급자 구독이나 모델을 포함하지 않습니다.

키는 브라우저 저장소나 프로젝트 DB에 기록하지 않고 현재 Python 프로세스 메모리에만 보관합니다. HTTP 응답은 키를 반환하지 않습니다. 서버 재시작 후 다시 연결하세요. OS의 프로세스 메모리 보호·디스크 암호화는 사용자 환경의 책임입니다.

CLI 환경변수를 사용하거나 비밀번호 입력으로 로컬 앱을 시작할 수 있습니다.

```powershell
$env:OPENDEVELOPER_BASE_URL = 'https://your-provider.example/v1'
$env:OPENDEVELOPER_MODEL = 'your-model-id'
# 키를 명령 기록에 남기지 않고 입력해서 localhost 앱 실행:
.\.venv\Scripts\opendeveloper.exe connect --base-url $env:OPENDEVELOPER_BASE_URL --model $env:OPENDEVELOPER_MODEL
```

비대화형 CLI는 환경의 `OPENDEVELOPER_API_KEY`, `OPENDEVELOPER_BASE_URL`, `OPENDEVELOPER_MODEL`을 읽습니다. 키를 Git에 커밋하거나 명령 인자로 전달하지 마세요. OpenDeveloper가 환경변수에서 주입받은 키는 연결 해제 후에도 환경에서 제거하기 전까지 사용될 수 있습니다.

## OAuth 연결

**공급자가 공식 지원하는 public client / Authorization Code + PKCE 앱**이 필요합니다. OAuth client ID를 발급받고 다음 콜백을 공급자 앱에 등록하세요.

```text
http://127.0.0.1:8765/oauth/callback
```

```powershell
$env:OPENDEVELOPER_OAUTH_CLIENT_ID = 'your-public-client-id'
$env:OPENDEVELOPER_OAUTH_AUTH_URL = 'https://provider.example/oauth/authorize'
$env:OPENDEVELOPER_OAUTH_TOKEN_URL = 'https://provider.example/oauth/token'
$env:OPENDEVELOPER_OAUTH_SCOPE = 'provider-documented-scopes'
.\.venv\Scripts\opendeveloper.exe serve
```

설정에서 API Base URL·모델을 저장하고 **OAuth 연결 → 인증 페이지 열기**를 누릅니다. 발급된 access token을 모델 API Bearer 토큰으로 사용합니다. state 검증, S256 PKCE, 10분 만료, 콜백 일회 사용을 적용합니다. 토큰 만료 시 다시 연결합니다. 자동 refresh, confidential client secret, 공급자별 특수 토큰 교환은 v0.1에서 지원하지 않습니다. ChatGPT·Claude 등의 웹 구독 로그인이 임의의 API 토큰을 제공한다는 의미가 아닙니다. 공급자마다 API 사용 권한과 OAuth 앱 등록 요건이 다릅니다.

## CLI

```text
opendeveloper plan https://example.com --brief "새 기능과 다른 디자인으로 만들어줘"
opendeveloper list
opendeveloper show PROJECT_ID
opendeveloper revise PROJECT_ID "모바일 우선으로 바꾸고 비교 기능 추가"
opendeveloper approve PROJECT_ID
opendeveloper build PROJECT_ID
opendeveloper serve --port 8765 --no-browser
```

`approve`는 전체 계획을 표시하고 `APPROVE`를 직접 입력받습니다. `build` 결과는 기본적으로 `~/.opendeveloper/PROJECT_ID/`에 저장됩니다. Windows에서는 `%USERPROFILE%\.opendeveloper`입니다. `--home PATH` 또는 `OPENDEVELOPER_HOME`으로 변경하세요. CLI와 웹은 같은 DB를 사용합니다. 같은 데이터 폴더에 서버를 여러 개 실행하지 마세요.

## 실제 지원 범위와 제한

- 분석: 공개 페이지의 서버 응답 HTML 텍스트와 폼·링크·버튼을 수집합니다. JavaScript 브라우저 렌더링, 로그인 세션, 스크린샷, 전체 사이트 크롤링은 지원하지 않습니다. SPA나 봇 차단 사이트는 정보가 부족하거나 분석에 실패할 수 있습니다.
- 생성: 브라우저에서 실행하는 정적 프론트엔드입니다. 결제·인증·실시간 서버 DB 등은 별도 백엔드 구현이 필요하며 실제 제공한다고 주장하지 않도록 지시합니다.
- UI: 원본 기능을 참고하되 브랜드·이미지·문구·정확한 레이아웃을 복제하지 않고 색상·구조·타이포그래피·상호작용을 새로 설계하도록 지시합니다. 생성물 품질과 독창성은 모델 결과를 확인해야 합니다.
- 검토: 모델의 정적 검토 및 파일 경로·크기 검사입니다. 생성된 앱의 브라우저 실행 테스트를 수행했다고 표시하지 않습니다. 생성 코드는 자동 실행하지 않습니다.
- 비용: 최초 계획 1회, 수정 요청 1회당 1회, 생성·검토 2~3회 모델 호출을 사용합니다. 90초 네트워크 타임아웃, 최대 3MB 응답, 생성물 최대 20개 파일·2MB를 적용합니다. 공급자 과금은 별도입니다.
- 실패: 모델 오류나 검토 미통과 시 다운로드를 제공하지 않고 승인 상태로 돌아가 재시도할 수 있습니다. 생성 중 Ctrl+C/강제 종료하면 상태가 `building`으로 남을 수 있습니다. 해당 프로젝트의 URL·요구사항으로 새 계획을 만들어 진행하세요.
- 데이터: 프로젝트와 메모는 로컬 SQLite에 보관합니다. 삭제하려면 서버를 종료한 후 해당 데이터 폴더를 삭제하세요. 분석한 페이지 텍스트·계획·요청·생성 코드는 선택한 모델 공급자에게 전송됩니다.

## 보안 경계

서버는 `127.0.0.1`에만 바인딩하고 Host·Origin·요청 토큰을 확인합니다. 인터넷에 공개하거나 리버스 프록시로 노출하지 마세요. 사이트/API/OAuth 네트워크 요청은 공개 HTTPS 443만 허용하고 DNS 주소를 고정하여 사설망 접근을 차단합니다. API 리디렉션에는 토큰을 전달하지 않습니다. 로컬 Ollama 같은 HTTP 서버는 현재 지원하지 않습니다.

생성 HTML은 다운로드 첨부파일로만 제공하고 localhost 앱 안에서 실행하지 않습니다. 모델 출력은 신뢰할 수 없는 코드입니다. 실행·배포 전 코드를 검토하고, 민감 계정으로 로그인한 브라우저와 분리된 환경에서 확인하세요. 메모는 짧은 구현 결정·검토 결과이며 비공개 추론 기록을 수집하지 않습니다.

자신의 사이트 또는 분석·재구현 권한이 있는 사이트에 사용하세요. 수집 시 robots 정책·약관·저작권을 확인하세요. 로그인·봇 차단을 우회하지 않습니다. robots.txt 자동 강제 기능은 포함하지 않습니다.

## 개발·검증

```sh
python -m unittest discover -s tests -v
python -m compileall -q opendeveloper
```

테스트는 네트워크·모델 fixture로 승인 경계, 계획 변경, ZIP, SSRF, 경로 검증, CSRF·Host·Origin, OAuth state·PKCE 및 HTTP 전체 흐름을 확인합니다. 실제 API 키 없이 실행할 수 있습니다. Windows/Linux Python 3.11·3.13 CI를 포함합니다. 실제 공급자 API·OAuth 및 Windows 설치는 별도 실기기 검증이 필요합니다.

## GitHub에 게시

이 소스는 공개 MIT 프로젝트로 게시할 수 있도록 준비되어 있습니다. GitHub CLI가 설치·인증된 환경에서는 소스 폴더에서 다음으로 새 저장소를 만들고 첫 커밋을 올릴 수 있습니다.

```sh
git init -b main
git add .
git commit -m "Initial OpenDeveloper release"
gh repo create opendeveloper --public --source=. --remote=origin --push
```

저장소가 이미 있다면 `gh repo create` 대신 해당 remote를 연결하세요. PyPI에는 아직 게시되지 않았으며, 동명의 PyPI 패키지를 설치하는 방식으로 안내하지 않습니다.

## 기여

이슈에 기대 동작·실제 동작·재현 절차를 기록해주세요. 키·OAuth code·분석 대상 개인정보는 첨부하지 마세요. PR은 기존 테스트와 추가 경계 테스트를 통과해야 합니다. 자세한 구조는 [ARCHITECTURE.md](ARCHITECTURE.md)를 참고하세요.

MIT License.
