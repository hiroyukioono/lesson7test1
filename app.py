import base64
import io
import os

import qrcode
from flask import Flask, render_template_string, request
from PIL import Image

app = Flask(__name__)

MAX_TEXT_LENGTH = 500
MAX_SIZE = 1024

HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>QRコード生成ツール</title>
    <style>
        body {
            font-family: sans-serif;
            max-width: 700px;
            margin: 40px auto;
            padding: 0 20px;
        }

        h1 {
            margin-bottom: 30px;
        }

        label {
            display: block;
            margin-top: 15px;
            font-weight: bold;
        }

        textarea,
        input,
        select {
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
            margin-top: 6px;
            font-size: 16px;
        }

        textarea {
            height: 120px;
        }

        button {
            margin-top: 20px;
            padding: 12px 25px;
            font-size: 16px;
            cursor: pointer;
        }

        .error {
            margin: 20px 0;
            padding: 12px;
            background: #ffe5e5;
            color: #b00000;
        }

        .result {
            margin-top: 30px;
            text-align: center;
        }

        .result img {
            max-width: 100%;
            height: auto;
            image-rendering: pixelated;
        }

        .download {
            display: inline-block;
            margin-top: 15px;
            padding: 10px 20px;
            background: #333;
            color: white;
            text-decoration: none;
        }
    </style>
</head>
<body>

<h1>QRコード生成ツール</h1>

<form method="post">
    <label for="text">テキスト（必須・最大500文字）</label>
    <textarea id="text" name="text" maxlength="500"
              required>{{ text }}</textarea>

    <label for="size">サイズ（ピクセル）</label>
    <input id="size" type="number" name="size"
           value="{{ size }}" min="100" max="1024">

    <label for="border">余白（border）</label>
    <input id="border" type="number" name="border"
           value="{{ border }}" min="0" max="20">

    <label for="error_correction">誤り訂正レベル</label>
    <select id="error_correction" name="error_correction">
        <option value="L" {% if error_correction == "L" %}selected{% endif %}>
            L（約7%）
        </option>
        <option value="M" {% if error_correction == "M" %}selected{% endif %}>
            M（約15%）
        </option>
        <option value="Q" {% if error_correction == "Q" %}selected{% endif %}>
            Q（約25%）
        </option>
        <option value="H" {% if error_correction == "H" %}selected{% endif %}>
            H（約30%）
        </option>
    </select>

    <button type="submit">QRコードを生成</button>
</form>

{% if error %}
<div class="error">{{ error }}</div>
{% endif %}

{% if qr_data %}
<div class="result">
    <h2>QRコード</h2>

    <img src="{{ qr_data }}" alt="生成されたQRコード">

    <br>

    <a class="download"
       href="{{ qr_data }}"
       download="qrcode.png">
        PNGをダウンロード
    </a>
</div>
{% endif %}

</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    text = ""
    size = 300
    border = 4
    error_correction = "M"
    qr_data = None
    error = None

    if request.method == "POST":
        text = request.form.get("text", "").strip()

        try:
            size = int(request.form.get("size", "300"))
            border = int(request.form.get("border", "4"))
        except ValueError:
            error = "サイズと余白には数値を入力してください。"
            size = 300
            border = 4

        error_correction = request.form.get(
            "error_correction", "M"
        ).upper()

        if not text:
            error = "テキストを入力してください。"
        elif len(text) > MAX_TEXT_LENGTH:
            error = f"テキストは{MAX_TEXT_LENGTH}文字以内で入力してください。"
        elif size < 100 or size > MAX_SIZE:
            error = f"サイズは100～{MAX_SIZE}pxで指定してください。"
        elif border < 0 or border > 20:
            error = "余白は0～20の範囲で指定してください。"
        elif error_correction not in ("L", "M", "Q", "H"):
            error = "誤り訂正レベルはL/M/Q/Hから選択してください。"

        if error is None:
            correction_map = {
                "L": qrcode.constants.ERROR_CORRECT_L,
                "M": qrcode.constants.ERROR_CORRECT_M,
                "Q": qrcode.constants.ERROR_CORRECT_Q,
                "H": qrcode.constants.ERROR_CORRECT_H,
            }

            try:
                qr = qrcode.QRCode(
                    version=None,
                    error_correction=correction_map[error_correction],
                    box_size=10,
                    border=border,
                )

                qr.add_data(text)
                qr.make(fit=True)

                image = qr.make_image(
                    fill_color="black",
                    back_color="white"
                ).convert("RGB")

                # 指定されたピクセルサイズに変更
                image = image.resize(
                    (size, size),
                    Image.Resampling.NEAREST
                )

                buffer = io.BytesIO()
                image.save(buffer, format="PNG")

                encoded = base64.b64encode(
                    buffer.getvalue()
                ).decode("ascii")

                qr_data = f"data:image/png;base64,{encoded}"

            except Exception as exc:
                error = f"QRコードの生成に失敗しました: {exc}"

    return render_template_string(
        HTML,
        text=text,
        size=size,
        border=border,
        error_correction=error_correction,
        qr_data=qr_data,
        error=error,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"

    print(f"Server started: http://localhost:{port}")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )