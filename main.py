from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import shutil
import uuid
import time

app = FastAPI()

# Конфигурация
SECRET_PIN = "1234"  # Поменяйте на свой ПИН-код для защиты сервиса
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Хранилище в памяти для текста/кода
latest_code = {
    "text": "# Вставьте ваш Python-код сюда",
    "updated_at": time.strftime("%H:%M:%S")
}

# Вспомогательная функция проверки доступа
def check_pin(x_pin: str = Header(None)):
    if x_pin != SECRET_PIN:
        raise HTTPException(status_code=401, detail="Неверный ПИН-код")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Quick Cloud Drop</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-900 text-gray-100 min-h-screen p-4 md:p-8">
        <div class="max-w-2xl mx-auto space-y-6">
            <header class="flex justify-between items-center bg-gray-800 p-4 rounded-xl border border-gray-700">
                <h1 class="text-xl font-bold text-blue-400">⚡ Quick Drop</h1>
                <input type="password" id="pinInput" placeholder="ПИН-код" 
                       class="bg-gray-900 border border-gray-600 rounded px-3 py-1 text-sm w-28 focus:outline-none focus:border-blue-500"
                       onchange="savePin(this.value)">
            </header>

            <!-- Блок передачи текста / кода -->
            <div class="bg-gray-800 p-5 rounded-xl border border-gray-700 space-y-3">
                <div class="flex justify-between items-center">
                    <h2 class="font-semibold text-lg">Код / Текст</h2>
                    <button onclick="copyCode()" class="bg-gray-700 hover:bg-gray-600 text-xs px-3 py-1.5 rounded transition">Скопировать</button>
                </div>
                <textarea id="codeText" class="w-full h-44 bg-gray-900 p-3 rounded-lg font-mono text-sm text-green-400 border border-gray-700 focus:outline-none focus:border-blue-500" placeholder="Вставьте код или текст..."></textarea>
                <div class="flex gap-2">
                    <button onclick="sendCode()" class="w-full bg-blue-600 hover:bg-blue-500 py-2 rounded-lg font-semibold text-sm transition">Отправить / Обновить</button>
                    <button onclick="fetchCode()" class="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded-lg text-sm transition">Обновить</button>
                </div>
            </div>

            <!-- Блок передачи файлов -->
            <div class="bg-gray-800 p-5 rounded-xl border border-gray-700 space-y-3">
                <h2 class="font-semibold text-lg">Загрузка файла</h2>
                <input type="file" id="fileInput" class="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-500"/>
                <button onclick="sendFile()" class="w-full bg-green-600 hover:bg-green-500 py-2 rounded-lg font-semibold text-sm transition">Загрузить файл</button>
                
                <hr class="border-gray-700 my-4">
                
                <h3 class="font-semibold text-sm text-gray-400">Файлы на сервере:</h3>
                <ul id="fileList" class="space-y-2 text-sm"></ul>
            </div>
        </div>

        <script>
            // Сохранение и получение ПИН-кода из браузера
            function getPin() { return localStorage.getItem('drop_pin') || ''; }
            function savePin(val) { localStorage.setItem('drop_pin', val); loadAll(); }
            document.getElementById('pinInput').value = getPin();

            async function sendCode() {
                const text = document.getElementById('codeText').value;
                const res = await fetch('/api/code', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'x-pin': getPin()},
                    body: JSON.stringify({text: text})
                });
                if (res.ok) alert('Сохранено!'); else alert('Ошибка авторизации (проверьте ПИН)');
            }

            async function fetchCode() {
                const res = await fetch('/api/code', { headers: {'x-pin': getPin()} });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('codeText').value = data.text;
                }
            }

            async function sendFile() {
                const input = document.getElementById('fileInput');
                if (!input.files.length) return alert('Выберите файл');
                const formData = new FormData();
                formData.append('file', input.files[0]);

                const res = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {'x-pin': getPin()},
                    body: formData
                });
                if (res.ok) {
                    input.value = '';
                    loadFiles();
                } else {
                    alert('Ошибка загрузки');
                }
            }

            async function loadFiles() {
                const res = await fetch('/api/files', { headers: {'x-pin': getPin()} });
                if (res.ok) {
                    const files = await res.json();
                    const list = document.getElementById('fileList');
                    list.innerHTML = files.map(f => `
                        <li class="flex justify-between items-center bg-gray-900 p-2 rounded border border-gray-700">
                            <span class="truncate max-w-xs">${f}</span>
                            <a href="/api/download/${f}?pin=${getPin()}" class="text-blue-400 hover:underline text-xs">Скачать</a>
                        </li>
                    `).join('');
                }
            }

            function copyCode() {
                const copyText = document.getElementById("codeText");
                copyText.select();
                navigator.clipboard.writeText(copyText.value);
                alert("Скопировано в буфер обмена!");
            }

            function loadAll() { fetchCode(); loadFiles(); }
            loadAll();
        </script>
    </body>
    </html>
    """

@app.get("/api/code", dependencies=[Depends(check_pin)])
async def get_code():
    return latest_code

@app.post("/api/code", dependencies=[Depends(check_pin)])
async def save_code(data: dict):
    latest_code["text"] = data.get("text", "")
    return {"status": "ok"}

@app.post("/api/upload", dependencies=[Depends(check_pin)])
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "ok"}

@app.get("/api/files", dependencies=[Depends(check_pin)])
async def list_files():
    return os.listdir(UPLOAD_DIR)

@app.get("/api/download/{filename}")
async def download_file(filename: str, pin: str):
    if pin != SECRET_PIN:
        raise HTTPException(status_code=401, detail="Неверный ПИН-код")
    file_path = os.path.join(UPLOAD_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Файл не найден")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
