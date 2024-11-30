from flask import Flask, request, redirect, url_for, flash, render_template, send_from_directory, jsonify, send_from_directory, render_template_string
import mimetypes
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime
from PIL import Image
import hashlib

app = Flask(__name__)

app.config['SECRET_KEY'] = 'mysecretkey'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1000 * 1000  # 16 MB



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'heic', 'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Verificar se o arquivo foi enviado
        if 'file' not in request.files:
            flash('Nenhuma parte do arquivo', 'erro')
            return redirect(request.url)
        
        file = request.files['file']
        
        # Verificar se o arquivo foi selecionado
        if file.filename == '':
            flash('Nenhum arquivo selecionado', 'erro')
            return jsonify({"message": F"Error ao enviar o arquivo, nenhum arquivo selecionado"}), 400
        
        # Verificar tamanho máximo
        if request.content_length > app.config['MAX_CONTENT_LENGTH']:
            print("Error")
            flash('Tamanho máximo excedido (16 MB)', 'erro')
            return jsonify({"message": f"Error ao enviar o arquivo {file.filename}, tamanho máximo do arquivo atingido 16MB"}), 413
        
        # Verificar formato suportado
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Verificar se o arquivo já existe e renomear corretamente
            name, ext = os.path.splitext(filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            counter = 1

            # Verificar se o nome do arquivo já tem um número e extraí-lo
            match = re.match(r"(.*?)(_([0-9]+))?$", name)
            if match:
                base_name = match.group(1)
                if match.group(3):
                    counter = int(match.group(3)) + 1
                else:
                    counter = 2  # Se o nome não tiver número, começamos pelo 2

            # Verificar se o arquivo já existe e incrementar o número do arquivo
            while os.path.exists(file_path):
                filename = f"{base_name}_{counter}{ext}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                counter += 1
            
            file.save(file_path)
             # Extrair metadados
            # Extrair metadados
            metadata = {
                'nome': filename,
                'tamanho_bytes': request.content_length,
                'tamanho_mb': round(request.content_length / (1024 * 1024), 2),
                'tipo': file.content_type,
                'data_envio': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'extensao': ext[1:],
                'data_criacao': datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S"),
                'data_modificacao': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S"),
                'md5_hash': hashlib.md5(open(file_path, 'rb').read()).hexdigest(),
                'sha1_hash': hashlib.sha1(open(file_path, 'rb').read()).hexdigest(),
            }
            
            # Adicionar metadados específicos para imagens
            if file.content_type.startswith('image/'):
                from PIL import Image
                img = Image.open(file_path)
                metadata['resolucao'] = f"{img.width}x{img.height}"
            
            message = {"message": f"Arquivo {filename} recebido com sucesso!", "metadata": metadata}

            print(message)

            return jsonify({"message": f"Arquivo {filename} recebido com sucesso!"}), 200

        else:
            flash('Formato não suportado', 'erro')
            return jsonify({"message": f"Error ao enviar o arquivo {file.filename}, formato não suportado"}), 400
        
    return render_template('index.html')


@app.route('/find_file', methods=['GET','POST'])
def find_file_input():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            return redirect(url_for('find_file', name=name))
        else:
            flash('Nome do arquivo não foi informado', 'erro')
            return jsonify({"message": "Nome do arquivo não foi informado"}), 400
    return render_template('input.html')


@app.route('/find_file/<name>')
def find_file(name):

    # Sanitize o nome do arquivo
    name = secure_filename(name)
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], name)

    if not os.path.exists(file_path):
        return "File not found"

    file_extension = os.path.splitext(name)[1].lower()

    if allowed_file(name):
        if file_extension in {'.png', '.jpg', '.jpeg', '.gif', '.heic'}:
            return redirect(url_for('show_img', name=name))
        else:
            return redirect(url_for('show_file', name=name))
    return "Invalid file type"

@app.route('/show_file/<name>')
def show_file(name):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], name)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

@app.route('/show_img/<name>')
def show_img(name):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], name)
    if not os.path.exists(file_path):
        return "File not found", 404
    # Renderiza a imagem em um HTML
    return render_template("img.html", name=name)

@app.route('/static/<name>')
def static_file(name):
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], name)
    if not os.path.exists(file_path):
        return "File not found", 404
    # Serve a imagem diretamente
    return send_from_directory(app.config["UPLOAD_FOLDER"], name)

@app.route('/list_files', methods=['GET'])
def list_files():
    files = []
    for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
        if allowed_file(filename):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            size_bytes = os.path.getsize(file_path)
            size_kb = size_bytes / 1024

            if size_kb >= 1024:
                size = f"{size_kb/1024:.2f} MB"
            else:
                size = f"{size_kb:.2f} KB"
                
            metadata = {
                'nome': filename,
                'tamanho_bytes': size_bytes,
                'tamanho_mb': round(size_bytes / (1024 * 1024), 2),
                'tipo': mimetypes.guess_type(file_path)[0],
                'data_envio': datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S"),
                'extensao': os.path.splitext(filename)[1][1:],
                'md5_hash': hashlib.md5(open(file_path, 'rb').read()).hexdigest(),
                'sha1_hash': hashlib.sha1(open(file_path, 'rb').read()).hexdigest(),
            }
            
            if mimetypes.guess_type(file_path)[0].startswith('image/'):
                from PIL import Image
                img = Image.open(file_path)
                metadata['resolucao'] = f"{img.width}x{img.height}"
                
            files.append({
                'name': filename,
                'size': size,
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%d/%m/%Y %H:%M:%S"),
                'metadata': metadata
            })
    
    return jsonify({'files': files})


@app.errorhandler(413)
def tamanho_maximo_excedido(e):
    return jsonify({"message": "Tamanho máximo excedido (16 MB)"}), 413

if __name__ == '__main__':
    app.run(debug=True, port=8000, host="0.0.0.0")
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)