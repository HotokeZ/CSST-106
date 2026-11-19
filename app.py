"""Local Flask interface. Run: python app.py. Load only trusted local model files."""
import base64
import os
from dataclasses import replace
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, abort
from PIL import Image, UnidentifiedImageError

from bigascheck.model import analyze, load_model
from bigascheck.vision import Settings, annotate, backend, load_rgb, png_bytes
from bigascheck.samples import SampleCatalog, SampleError


def create_app(model_path=None, samples_root=None, feature_table=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024
    path = Path(model_path or os.environ.get("BIGASCHECK_MODEL", "artifacts/model.joblib"))
    project = Path(__file__).resolve().parent
    samples = SampleCatalog(samples_root or project / "data/splits",
                            feature_table or project / "artifacts/features_and_splits.csv")
    bundle, model_error = None, None
    if path.is_file():
        try:
            bundle = load_model(path)
        except (ValueError, OSError, KeyError) as exc:
            model_error = str(exc)

    @app.get("/")
    def home():
        return render_template("index.html", trained=bundle is not None, backend=backend(),
                               settings=bundle["settings"] if bundle else None, model_error=model_error)

    @app.get("/api/status")
    def status():
        return jsonify(trained=bundle is not None, backend=backend(), model_error=model_error)

    @app.get("/api/samples")
    def list_samples():
        try:
            page = int(request.args.get("page", 1))
            size = int(request.args.get("page_size", 6))
        except ValueError:
            return jsonify(error="Page and page size must be integers."), 400
        if page < 1 or not 1 <= size <= 24 or request.args.get("label", "all") not in {"all", "whole", "broken", "mixed"}:
            return jsonify(error="Invalid sample filter or page."), 400
        try:
            return jsonify(samples.list(request.args.get("label", "all"), page, size))
        except (SampleError, OSError) as exc:
            return jsonify(error=str(exc) if isinstance(exc, SampleError) else "Test samples are unavailable."), 503

    @app.get("/api/samples/<sample_id>/image")
    def sample_image(sample_id):
        try:
            return send_file(samples.asset(sample_id, thumbnail=request.args.get("thumbnail") == "1"), conditional=True)
        except KeyError:
            abort(404)
        except (SampleError, OSError):
            return jsonify(error="This test sample is unavailable."), 404

    @app.post("/api/analyze")
    def analyze_image():
        upload = request.files.get("image")
        sample_id = request.form.get("sample_id", "").strip()
        has_upload = upload is not None and bool(upload.filename)
        if has_upload and sample_id:
            return jsonify(error="Choose a photo upload or a test sample, not both."), 400
        if not has_upload and not sample_id:
            return jsonify(error="Upload a rice photograph or choose a test sample first."), 400
        try:
            sample = samples.get(sample_id) if sample_id else None
            rgb = load_rgb(samples.asset(sample_id) if sample_id else upload.stream)
            base_settings = Settings(**bundle["settings"]) if bundle else Settings()
            settings = replace(base_settings, background=request.form.get("background", "auto"),
                               min_area=int(request.form.get("min_area", base_settings.min_area)),
                               split_touching=request.form.get("split_touching", "true") == "true")
            result, mask = analyze(rgb, bundle, settings, request.form.get("method", "decision_tree"))
            result["annotated_png"] = base64.b64encode(png_bytes(annotate(rgb, result["grains"]))).decode()
            result["mask_png"] = base64.b64encode(png_bytes(Image.fromarray(mask))).decode()
            if sample is not None:
                result["sample"] = samples.public(sample)
            return jsonify(result)
        except KeyError:
            return jsonify(error="Test sample not found."), 404
        except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
            return jsonify(error=f"Cannot analyze this image: {exc}"), 400

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Choose an image smaller than 15 MB."), 413

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
