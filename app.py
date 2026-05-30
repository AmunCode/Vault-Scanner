import os
from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceNotFoundError

app = Flask(__name__)


def get_available_filename(container_client, prefix):
    """Return the next available filename for a given barcode prefix."""
    base = f"{prefix}.jpg"
    try:
        container_client.get_blob_client(base).get_blob_properties()
    except ResourceNotFoundError:
        return base

    counter = 1
    while True:
        name = f"{prefix}({counter}).jpg"
        try:
            container_client.get_blob_client(name).get_blob_properties()
            counter += 1
        except ResourceNotFoundError:
            return name


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    barcode = request.form.get("barcode", "").strip()
    if not barcode:
        return jsonify({"error": "Barcode is required"}), 400

    image = request.files.get("image")
    if not image:
        return jsonify({"error": "Image is required"}), 400

    prefix = barcode[:6]

    try:
        conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        container = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "vault-scans")

        service = BlobServiceClient.from_connection_string(conn_str)
        container_client = service.get_container_client(container)

        try:
            container_client.create_container()
        except Exception:
            pass

        filename = get_available_filename(container_client, prefix)

        container_client.get_blob_client(filename).upload_blob(
            image.read(),
            overwrite=False,
            content_settings=ContentSettings(content_type="image/jpeg"),
        )

        return jsonify({"success": True, "filename": filename})

    except KeyError:
        return jsonify({"error": "Storage not configured"}), 500
    except Exception as e:
        app.logger.error("Upload failed: %s", e)
        return jsonify({"error": "Upload failed"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
