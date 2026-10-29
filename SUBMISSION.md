# 과제 제출: Todo 앱과 PRD

- GitHub: https://github.com/castlegyun/todo-app
- PRD: [PRD.md](PRD.md)
- 코드: 이 저장소 (백엔드 `app.py`, 화면 `static/`, DB 설정 `supabase_schema.sql`)
- 실행 방법: [README.md](README.md)

## 기록 (한 줄씩)
- **클라우드 전환:** 길 A(로컬 SQLite `todo.db`)에서 길 B(Supabase Postgres + Supabase Auth)로 전환했다. 화면은 백엔드 `/api`에만 요청하고, 키는 백엔드 `.env`에서만 쓴다.
- **RLS 확인:** `todo` 표에 RLS를 켜고 정책을 두었다. 계정 2개로 확인한 결과 B는 A의 할 일이 보이지 않고, 수정·삭제는 0건이며, A의 `user_id`로 위조해 추가하면 `new row violates row-level security policy`(403)로 거부되고, 로그인 없는 접근은 401로 막혔다.

## 확인 결과

### 1) 로컬(SQLite): CRUD와 껐다 켜도 데이터 유지
| 확인 | 결과 |
|---|---|
| 추가·완료·삭제 | 동작 (브라우저 확인, `evidence/00-local-sqlite-ui.png`) |
| 서버를 껐다 켜도 데이터 유지 | 유지 (서버 재시작 후 목록 조회로 확인) |
| 오늘 할 일만 보기 | 오늘 마감 항목만 표시 |

로컬 확인은 SQLite 버전에서 했고, 그 코드는 `legacy-sqlite/`에 보관했다. 화면은 로그인 기능을 넣기 전의 것이다.

### 2) 클라우드(Supabase): CRUD와 껐다 켜도 데이터 유지
| 장면 | 파일 |
|---|---|
| 로그인 화면 | `evidence/01-login-screen.png` |
| 할 일 목록 (마감 지남 표시, 완료 항목) | `evidence/02-list.png` |
| 오늘 할 일만 보기 | `evidence/03-today-filter.png` |
| 완료 체크 (취소선) | `evidence/04-completed.png` |
| 완료 후 오늘 필터가 비어 있음 | `evidence/04b-today-after-complete.png` |
| 삭제 후 목록 | `evidence/05-deleted.png` |
| **서버를 껐다 켠 뒤 새로고침해도 데이터 유지** | `evidence/06-after-server-restart.png` |
| **다른 계정(B)으로 로그인하면 목록이 비어 있음 (RLS)** | `evidence/07-user-b-sees-nothing.png` |

### 3) RLS 확인 상세 (실제 Supabase, 계정 A·B)
| 시도 | 결과 |
|---|---|
| 로그인 없이 `/api/todos` | 401 |
| 로그인 없이 DB 직접 조회 | 401 (권한 없음) |
| B가 A의 할 일 조회 | 0건 |
| B가 A의 할 일 수정·삭제 (API) | 404 |
| B가 A의 할 일 수정·삭제 (DB 직접 호출) | 0건 변경 |
| B가 A의 `user_id`로 INSERT 위조 | 403, `new row violates row-level security policy` |
| 추가한 행의 소유자 | 로그인한 사용자 id가 `user_id`에 자동 저장됨 |

## 배포
- 접속 URL: https://todo-app-iw2l.onrender.com
- 플랫폼: Render (무료 플랜, `render.yaml`). 유휴 후 첫 접속은 30~60초 걸릴 수 있다.
- 확인: 화면 200, 로그인 없이 `/api/todos` 401.
