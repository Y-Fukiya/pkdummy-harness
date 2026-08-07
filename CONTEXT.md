# PK Workflow Fixture Library

出典付きPK要約を1-compartmentデモと下流解析用の再現可能なworkflow fixtureに変換するドメイン。

## Language

**Canonical PK library**:
出典、元文、解析値、導出値の対応が保持された薬剤別PK情報。デモの実行結果に合わせて自動修正しない。
_Avoid_: デモパラメータ、生成値

**PK workflow fixture**:
PK関連ツールの接続とデータ処理を検査するための合成データセット。臨床的予測または申請用データではない。
_Avoid_: 臨床データ、バリデーションデータ

**Dense simulated concentration**:
観測スケジュールより細かい時間間隔で作られた被験者別の濃度推移。
_Avoid_: PCデータ、実測濃度

**Clinical sample**:
名目採血スケジュールに従ってdense simulated concentrationから抽出された1例1時点の観測fixture。
_Avoid_: 原シミュレーション行、実検体

**DM fixture**:
被験者ID、年齢、性別、armを保持する限定版人口統計ドメイン。
_Avoid_: submission-ready DM

**EX fixture**:
被験者ごとの被験薬、用量、単位、投与経路、投与時点を保持する限定版曝露ドメイン。
_Avoid_: submission-ready EX

**PC fixture**:
被験者、採血時点、濃度、単位、BLQ/MDV関連情報を保持する限定版薬物濃度ドメイン。
_Avoid_: dense simulated concentration、submission-ready PC

**Limited SDTM-like domain**:
SDTMに似た列名と結合キーを持つworkflow fixture。submission-ready SDTMまたはXPTではない。
_Avoid_: SDTM、submission dataset
