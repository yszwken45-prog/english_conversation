1. ダッシュボード（学習・利用状況の可視化）
SaaSにおいて、ユーザーが「自分の成長や利用量」を確認できるページは必須です。

内容: ログイン後のトップ画面に、これまでの「総会話数」「学習時間」「最近使った単語」などをグラフや数字で表示します。

Claude Codeへの指示: "Create a dashboard page using streamlit's metrics and charts to visualize the user's historical activity from the SQLite database."

2. プロフィール設定と「AIのパーソナライズ」
ユーザーごとにAIの振る舞いを変えられる機能です。

内容: 「初心者モード」「ビジネス英語モード」などの設定を保存できるようにします。

SaaS的価値: 「自分専用のツール」という感覚を強め、チャーン（解約）を防ぐ重要な要素です。

Claude Codeへの指示: "Add a settings page where users can update their profile and select AI persona preferences (e.g., tone, difficulty level), and ensure these are reflected in the system prompt."

3. 管理者用ページ（簡易版）
自分（運営者）が、今何人のユーザーがいて、誰がどれくらい使っているかを確認する画面です。

内容: ユーザー一覧や、APIの総消費量などを表示します。

アピールポイント: 「BtoBや本格的なサービス運用を見据えた設計ができる」という印象を与えます。

Claude Codeへの指示: "Add a secret admin-only page that displays a table of all registered users and their total message counts for monitoring purposes."