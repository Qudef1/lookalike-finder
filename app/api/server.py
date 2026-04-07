"""
FastAPI сервер для запуска Lookalike Finder пайплайна.

Запуск:
    uvicorn server:app --reload --port 8000

Эндпоинты:
    POST   /api/run           — запустить пайплайн для компании
    GET    /api/jobs/{id}     — проверить статус и результат
    GET    /                  — веб-интерфейс
"""

import os
import json
import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.company_profile import build_full_pipeline

app = FastAPI(title="Lookalike Finder API")

# Хранилище задач (в памяти)
jobs: dict[str, dict] = {}


class RunRequest(BaseModel):
    company_name: str


class RunResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    company_name: str
    status: str  # pending | running | done | failed
    created_at: str
    completed_at: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


def _run_pipeline(job_id: str, company_name: str):
    """Фоновое выполнение пайплайна."""
    jobs[job_id]["status"] = "running"
    jobs[job_id]["message"] = "Пайплайн запущен..."

    print(f"\n{'='*60}")
    print(f"[JOB {job_id[:8]}] Запуск для компании: {company_name}")
    print(f"{'='*60}")

    try:
        result = build_full_pipeline(company_name)

        if "error" in result:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result["error"]
            print(f"[JOB {job_id[:8]}] Ошибка: {result['error']}")
        else:
            jobs[job_id]["status"] = "done"
            jobs[job_id]["result"] = result
            _save_pipeline_results(job_id, result)
            print(f"[JOB {job_id[:8]}] Завершён успешно")
            print(f"  Профиль: {result.get('profile', {}).get('company_name', 'N/A')}")
            print(f"  Запросов: {len(result.get('queries', []))}")

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        print(f"[JOB {job_id[:8]}] Исключение: {e}")

    jobs[job_id]["completed_at"] = datetime.now().isoformat()


def _save_pipeline_results(job_id: str, result: dict):
    """Сохраняет результаты пайплайна в файлы."""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app", "output")
    if "similar_companies_md" in result:
        with open(os.path.join(output_dir, "similar_companies.md"), "w", encoding="utf-8") as f:
            f.write(result["similar_companies_md"])
    if "tier_report_md" in result:
        with open(os.path.join(output_dir, "tier_report.md"), "w", encoding="utf-8") as f:
            f.write(result["tier_report_md"])
    if "profile" in result:
        with open(os.path.join(output_dir, "company_profile.json"), "w", encoding="utf-8") as f:
            json.dump(result["profile"], f, ensure_ascii=False, indent=2)


@app.get("/", response_class=HTMLResponse)
async def index():
    """Простой веб-интерфейс."""
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lookalike Finder</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 2rem; }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; color: #38bdf8; }
        .subtitle { color: #94a3b8; margin-bottom: 2rem; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px;
                padding: 1.5rem; margin-bottom: 1.5rem; }
        label { display: block; font-weight: 500; margin-bottom: 0.5rem; color: #cbd5e1; }
        input[type="text"] { width: 100%; padding: 0.75rem 1rem; border-radius: 8px;
            border: 1px solid #475569; background: #0f172a; color: #e2e8f0; font-size: 1rem;
            outline: none; transition: border-color 0.2s; }
        input[type="text"]:focus { border-color: #38bdf8; }
        button { width: 100%; padding: 0.75rem; border: none; border-radius: 8px;
            background: #0ea5e9; color: white; font-size: 1rem; font-weight: 600;
            cursor: pointer; transition: background 0.2s; margin-top: 1rem; }
        button:hover { background: #0284c7; }
        button:disabled { background: #475569; cursor: not-allowed; }
        .status { margin-top: 1rem; padding: 0.75rem 1rem; border-radius: 8px;
                  background: #0f172a; border: 1px solid #334155; font-family: monospace;
                  font-size: 0.875rem; display: none; }
        .status.visible { display: block; }
        .status.running { border-color: #fbbf24; color: #fbbf24; }
        .status.done { border-color: #34d399; color: #34d399; }
        .status.failed { border-color: #f87171; color: #f87171; }
        .spinner { display: inline-block; animation: spin 1s linear infinite; margin-right: 0.5rem; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .job-list { margin-top: 1.5rem; }
        .job-item { padding: 0.75rem 1rem; background: #0f172a; border: 1px solid #334155;
                   border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.875rem;
                   display: flex; justify-content: space-between; align-items: center; }
        .job-item .name { color: #e2e8f0; }
        .job-item .meta { color: #64748b; font-size: 0.75rem; }
        .badge { padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.7rem;
                 font-weight: 600; text-transform: uppercase; }
        .badge-running { background: #422006; color: #fbbf24; }
        .badge-done { background: #052e16; color: #34d399; }
        .badge-failed { background: #450a0a; color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Lookalike Finder</h1>
        <p class="subtitle">Поиск компаний, похожих по профилю</p>

        <div class="card">
            <label for="company">Название компании</label>
            <input type="text" id="company" placeholder="Например: Interexy MedKitDoc"
                   onkeydown="if(event.key==='Enter') runPipeline()">
            <button id="runBtn" onclick="runPipeline()">Запустить пайплайн</button>
            <div id="status" class="status"></div>
        </div>

        <div class="job-list" id="jobList"></div>
    </div>

    <script>
        async function runPipeline() {
            const company = document.getElementById('company').value.trim();
            if (!company) { alert('Введите название компании'); return; }

            const btn = document.getElementById('runBtn');
            const status = document.getElementById('status');
            btn.disabled = true;
            btn.textContent = '⏳ Запуск...';
            status.className = 'status visible running';
            status.innerHTML = '<span class="spinner">⟳</span> Пайплайн запущен...';

            try {
                const resp = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company_name: company })
                });
                const data = await resp.json();
                status.innerHTML = `<span class="spinner">⟳</span> Задача: ${data.job_id.slice(0,8)}<br>Статус: ${data.status}`;
                loadJobs();
                pollJob(data.job_id);
            } catch (e) {
                status.className = 'status visible failed';
                status.textContent = 'Ошибка: ' + e.message;
                btn.disabled = false;
                btn.textContent = 'Запустить пайплайн';
            }
        }

        async function pollJob(jobId) {
            const status = document.getElementById('status');
            const btn = document.getElementById('runBtn');
            const interval = setInterval(async () => {
                const resp = await fetch(`/api/jobs/${jobId}`);
                const data = await resp.json();
                loadJobs();

                if (data.status === 'done') {
                    clearInterval(interval);
                    status.className = 'status visible done';
                    status.textContent = `✅ Готово! Найдено компаний: ${data.result?.queries?.length || 0} запросов`;
                    btn.disabled = false;
                    btn.textContent = 'Запустить пайплайн';
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    status.className = 'status visible failed';
                    status.textContent = `❌ Ошибка: ${data.error}`;
                    btn.disabled = false;
                    btn.textContent = 'Запустить пайплайн';
                } else {
                    status.innerHTML = `<span class="spinner">⟳</span> Статус: ${data.status}`;
                }
            }, 5000);
        }

        async function loadJobs() {
            const resp = await fetch('/api/jobs');
            const jobs = await resp.json();
            const list = document.getElementById('jobList');
            if (jobs.length === 0) { list.innerHTML = ''; return; }
            list.innerHTML = '<h3 style="margin-bottom:0.75rem; color:#94a3b8;">Задачи</h3>' +
                jobs.map(j => {
                    const badgeClass = j.status === 'done' ? 'badge-done' :
                                       j.status === 'failed' ? 'badge-failed' : 'badge-running';
                    return `<div class="job-item">
                        <div><span class="name">${j.company_name}</span>
                             <div class="meta">${j.job_id.slice(0,8)} · ${j.created_at}</div></div>
                        <span class="badge ${badgeClass}">${j.status}</span>
                    </div>`;
                }).join('');
        }

        loadJobs();
    </script>
</body>
</html>
"""


@app.post("/api/run", response_model=RunResponse)
async def run_pipeline(req: RunRequest, bg: BackgroundTasks):
    """Запустить пайплайн для компании (фоновая задача)."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "company_name": req.company_name,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "result": None,
        "error": None,
        "message": "",
    }
    bg.add_task(_run_pipeline, job_id, req.company_name)
    return RunResponse(
        job_id=job_id,
        status="pending",
        message=f"Задача {job_id[:8]} добавлена в очередь",
    )


@app.get("/api/jobs")
async def list_jobs():
    """Список всех задач (только метаданные)."""
    return [
        {
            "job_id": j["job_id"],
            "company_name": j["company_name"],
            "status": j["status"],
            "created_at": j["created_at"],
        }
        for j in reversed(jobs.values())
    ]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Статус и результат конкретной задачи."""
    if job_id not in jobs:
        return {"error": "Job not found"}
    j = jobs[job_id]
    return {
        "job_id": j["job_id"],
        "company_name": j["company_name"],
        "status": j["status"],
        "created_at": j["created_at"],
        "completed_at": j["completed_at"],
        "result": j["result"],
        "error": j["error"],
    }
