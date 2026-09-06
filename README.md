# 算数ナビ AI先生（小学1〜3年）

文部科学省の小学校学習指導要領（算数）を骨格に、小学1〜3年の算数単元を動画教材・AI解説・YouTube字幕質問・答案写真添削につないだStreamlit試作版です。

## 起動

```bash
pip install -r requirements.txt
streamlit run app.py
```

## AI機能

AI先生、YouTube字幕への質問、答案画像添削にはOpenAI APIキーが必要です。

環境変数:

```bash
OPENAI_API_KEY=...
```

またはStreamlit CloudのSecretsに以下を設定します。

```toml
OPENAI_API_KEY = "..."
```

APIキーがなくても、学年別カリキュラム、単元の目標、教材リンク、学習済みチェックは利用できます。

## カリキュラムの基準

- 文部科学省「小学校学習指導要領（平成29年告示）解説 算数編」
- 教材例：NPO法人eboard、YouTube上の教育動画等

教科書会社によって単元名や掲載順は異なるため、アプリでは学習内容を理解しやすい単位に整理しています。
