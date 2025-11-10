FROM python:3.11-slim

WORKDIR /app

# Mettre à jour les dépôts et installer AMC + LaTeX
RUN apt-get update && apt-get install -y \
    auto-multiple-choice \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-lang-french \
    texlive-fonts-extra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]