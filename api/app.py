from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import os, shutil, subprocess, shlex, uuid
import stripe

AMC_DATA_DIR = os.getenv("AMC_DATA_DIR", "/amc/data")
CORS = os.getenv("CORS_ORIGINS", "*").split(",")

# Stripe (optionnel dev)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", None)
PRICE_ID_PRO = os.getenv("STRIPE_PRICE_ID_PRO", "")

app = FastAPI(title="AMC API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AMC_BIN = "auto-multiple-choice"

def run(cmd: str, cwd: str | None = None):
    p = subprocess.run(shlex.split(cmd), cwd=cwd,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise HTTPException(500, p.stdout)
    return p.stdout

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/projects")
async def create_project(project_id: str | None = Form(None)):
    pid = project_id or uuid.uuid4().hex[:8]
    proj_dir = os.path.join(AMC_DATA_DIR, pid)
    os.makedirs(proj_dir, exist_ok=True)
    # Donner les permissions dès la création
    os.chmod(proj_dir, 0o777)
    return {"project_id": pid}

@app.post("/projects/{project_id}/source")
async def upload_source(project_id: str, source: UploadFile = File(...)):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    if not os.path.isdir(proj_dir):
        raise HTTPException(404, "project not found")
    dst = os.path.join(proj_dir, source.filename)
    with open(dst, "wb") as f:
        shutil.copyfileobj(source.file, f)
    return {"saved": os.path.basename(dst)}

@app.post("/projects/{project_id}/prepare")
async def prepare(project_id: str, tex_filename: str = Form(...), n_copies: int = Form(1)):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    tex_path = os.path.join(proj_dir, tex_filename)
    if not os.path.exists(tex_path):
        raise HTTPException(400, "tex not found")
    
    # CRÉER TOUS LES DOSSIERS AVEC PERMISSIONS
    data_dir = os.path.join(proj_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    os.chmod(data_dir, 0o777)
    
    amc_data_dir = os.path.join(proj_dir, tex_filename.replace('.tex', '-data'))
    os.makedirs(amc_data_dir, exist_ok=True)
    os.chmod(amc_data_dir, 0o777)
    
    log = run(f"{AMC_BIN} prepare --project {proj_dir} --with pdflatex --n-copies {n_copies} --filter plain --source {tex_path}")
    return JSONResponse({"log": log})

@app.post("/projects/{project_id}/compile")
async def compile_pdf(project_id: str):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    
    # CORRECTION : Utiliser xelatex directement sur le fichier filtré
    tex_file = "test-exam_filtered.tex"  # Le fichier généré par AMC prepare
    tex_path = os.path.join(proj_dir, tex_file)
    
    if not os.path.exists(tex_path):
        raise HTTPException(400, "Fichier LaTeX filtré non trouvé")
    
    # Compiler avec xelatex
    log = run(f"xelatex -interaction=nonstopmode {tex_file}", cwd=proj_dir)
    
    # Vérifier si le PDF a été créé
    pdf_path = os.path.join(proj_dir, "test-exam_filtered.pdf")
    if os.path.exists(pdf_path):
        return JSONResponse({"log": log, "pdf_created": True})
    else:
        raise HTTPException(500, "Échec de la compilation PDF: " + log)

@app.get("/projects/{project_id}/pdf/{name}")
async def get_pdf(project_id: str, name: str):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    
    # Si name est "calage.pdf", servir le PDF compilé
    if name == "calage.pdf":
        pdf_path = os.path.join(proj_dir, "test-exam_filtered.pdf")
    else:
        pdf_path = os.path.join(proj_dir, name)
        
    if not (os.path.exists(pdf_path) and pdf_path.endswith(".pdf")):
        raise HTTPException(404, "PDF non trouvé")
    return FileResponse(pdf_path, media_type="application/pdf")

@app.post("/projects/{project_id}/scans")
async def upload_scans(project_id: str, scans: list[UploadFile] = File(...)):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    scans_dir = os.path.join(proj_dir, "scans")
    os.makedirs(scans_dir, exist_ok=True)
    os.chmod(scans_dir, 0o777)
    for uf in scans:
        dst = os.path.join(scans_dir, uf.filename)
        with open(dst, "wb") as f:
            shutil.copyfileobj(uf.file, f)
    log = run(f"{AMC_BIN} capture --project {proj_dir} --detect-barcodes --progress --copies-dir {scans_dir}")
    return {"log": log, "count": len(scans)}

@app.post("/projects/{project_id}/grade")
async def grade(project_id: str):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    log = run(f"{AMC_BIN} score --project {proj_dir} --strategy auto")
    return JSONResponse({"log": log})

@app.get("/projects/{project_id}/export/grades.csv")
async def export_grades(project_id: str):
    proj_dir = os.path.join(AMC_DATA_DIR, project_id)
    out_csv = os.path.join(proj_dir, "grades.csv")
    log = run(f"{AMC_BIN} export --project {proj_dir} --format CSV --o {out_csv}")
    if not os.path.exists(out_csv):
        raise HTTPException(500, "export failed")
    return FileResponse(out_csv, media_type="text/csv", filename="grades.csv")

# -------- Monétisation simple (Stripe Checkout) --------
@app.post("/billing/checkout")
async def create_checkout_session():
    if not stripe.api_key or not PRICE_ID_PRO:
        raise HTTPException(400, "Stripe non configuré (STRIPE_SECRET_KEY / STRIPE_PRICE_ID_PRO)")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": PRICE_ID_PRO, "quantity": 1}],
        success_url=os.getenv("SUCCESS_URL", "https://example.com/success"),
        cancel_url=os.getenv("CANCEL_URL", "https://example.com/cancel"),
        automatic_tax={"enabled": True},
        allow_promotion_codes=True,
    )
    return {"url": session.url}

@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, endpoint_secret) if endpoint_secret else {"type": "noop"}
    except Exception as e:
        raise HTTPException(400, str(e))
    # if event["type"] == "checkout.session.completed": activer l'abonnement
    return {"received": True}