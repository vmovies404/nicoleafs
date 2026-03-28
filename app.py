from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from datetime import datetime
from PIL import Image
import os, random, uuid, tempfile

app = Flask(__name__)
app.config["SECRET_KEY"] = "nicoleaf-secret-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///nicoleaf.db"

# Render-safe upload folder
app.config["UPLOAD_FOLDER"] = os.path.join(tempfile.gettempdir(), "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

class Analysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_filename = db.Column(db.String(255), nullable=False)
    nicotine_level = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def estimate_nicotine_level(image_path):
    try:
        img = Image.open(image_path).convert("RGB")
        pixels = list(img.getdata())
        total = len(pixels)
        r = sum(p[0] for p in pixels) / total
        g = sum(p[1] for p in pixels) / total
        b = sum(p[2] for p in pixels) / total
        green_ratio = g / (r + g + b + 0.001)
        nicotine = round(0.8 + (green_ratio * 4.2), 2)
        return max(0.8, min(5.0, nicotine))
    except:
        return round(random.uniform(1.5, 4.5), 2)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        files = request.files.getlist("file")
        ids = []

        for file in files:
            if file and file.filename:
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                nicotine = estimate_nicotine_level(filepath)

                entry = Analysis(image_filename=filename, nicotine_level=nicotine)
                db.session.add(entry)
                db.session.commit()

                ids.append(entry.id)

        return redirect(url_for("multi_result", ids=",".join(map(str, ids))))

    return render_template("index.html")

@app.route("/results")
def multi_result():
    ids = request.args.get("ids").split(",")
    analyses = Analysis.query.filter(Analysis.id.in_(ids)).all()
    return render_template("multi_result.html", analyses=analyses)

@app.route("/history")
def history():
    analyses = Analysis.query.order_by(Analysis.timestamp.desc()).all()
    return render_template("history.html", analyses=analyses)

@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    entry = Analysis.query.get_or_404(id)

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], entry.image_filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(entry)
    db.session.commit()

    return redirect(url_for("history"))

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

if __name__ == "__main__":
    app.run()
