import os
from flask import Flask, render_template, request, jsonify, make_response, send_from_directory
from models import db, Post
import uuid
import bleach
from werkzeug.utils import secure_filename
from PIL import Image
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'post-secret-key-2025'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///post.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# Создаем папку для загрузок, если её нет
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# CORS headers для всех ответов
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

ALLOWED_TAGS = ['h1', 'h2', 'p', 'br', 'strong', 'em', 'u', 'a', 'blockquote', 'ul', 'ol', 'li', 'img', 'figure', 'figcaption', 'iframe', 'video', 'div', 'code', 'pre', 'span']
ALLOWED_ATTRS = {
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'style', 'class'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen', 'class'],
    'video': ['src', 'controls', 'class', 'style'],
    'div': ['class', 'style'],
    'code': ['class', 'style'],
    'pre': ['class', 'style'],
    'span': ['class', 'style'],
}

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg'}

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def process_image(file):
    """Обработка изображения: оптимизация и создание превью"""
    try:
        img = Image.open(file)
        
        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        
        # Максимальный размер 2000px по большей стороне
        max_size = 2000
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Сохраняем оптимизированное изображение
        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        # Сохраняем с качеством 85%
        img.save(filepath, 'JPEG', quality=85, optimize=True)
        
        return filename, filepath
    except Exception as e:
        raise Exception(f"Ошибка обработки изображения: {str(e)}")

def is_video_url(url):
    """Проверяет, является ли URL ссылкой на видео (YouTube, Vimeo и т.д.)"""
    video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    return any(domain in url.lower() for domain in video_domains)

def convert_video_url_to_embed(url):
    """Конвертирует URL видео в embed код"""
    if 'youtube.com/watch' in url or 'youtu.be/' in url:
        # YouTube
        video_id = None
        if 'youtube.com/watch' in url:
            video_id = url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0]
        
        if video_id:
            return f'<div class="video-wrapper"><iframe src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>'
    
    elif 'vimeo.com' in url:
        # Vimeo
        video_id = url.split('/')[-1].split('?')[0]
        return f'<div class="video-wrapper"><iframe src="https://player.vimeo.com/video/{video_id}" frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe></div>'
    
    elif 'dailymotion.com' in url:
        # Dailymotion
        video_id = url.split('/video/')[1].split('?')[0] if '/video/' in url else url.split('/')[-1]
        return f'<div class="video-wrapper"><iframe src="https://www.dailymotion.com/embed/video/{video_id}" frameborder="0" allowfullscreen></iframe></div>'
    
    return None

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'image' not in request.files:
        return jsonify({'error': 'No file'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    try:
        if allowed_image_file(file.filename):
            # Обработка изображения
            filename, filepath = process_image(file)
            return jsonify({'url': f'/static/uploads/{filename}'})
        elif allowed_video_file(file.filename):
            # Загрузка видео
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4()}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return jsonify({'url': f'/static/uploads/{filename}', 'type': 'video'})
        else:
            return jsonify({'error': 'Неподдерживаемый формат файла'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    return render_template('editor.html', post=None)

@app.route('/save', methods=['POST'])
def save():
    try:
        if not request.is_json:
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_uuid = request.cookies.get('tph_uuid') or str(uuid.uuid4())
        content = data.get('content', '')
        
        # Обрабатываем видео ссылки
        import re
        # Ищем ссылки в тексте
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, content)
        
        for url in urls:
            if is_video_url(url):
                embed_code = convert_video_url_to_embed(url)
                if embed_code:
                    content = content.replace(url, embed_code)
        
        # Bleach очищает HTML, но сохраняет содержимое code/pre блоков как текст
        # HTML теги внутри code/pre уже экранированы через textContent в JavaScript
        # Bleach сам экранирует содержимое, если нужно, но для code/pre мы сохраняем как есть
        clean_content = bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=False)
        slug = Post.generate_unique_slug(data.get('title'))
        
        new_post = Post(
            title=data.get('title') or "Untitled",
            author_name=data.get('author_name'),
            content=clean_content,
            slug=slug,
            owner_uuid=user_uuid
        )
        db.session.add(new_post)
        db.session.commit()
        
        res = make_response(jsonify({'slug': slug}))
        res.set_cookie('tph_uuid', user_uuid, max_age=60*60*24*365*10)
        return res
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/<slug>')
def view_post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    can_edit = (request.cookies.get('tph_uuid') == post.owner_uuid)
    return render_template('view.html', post=post, can_edit=can_edit)

@app.route('/delete/<slug>', methods=['POST'])
def delete_post(slug):
    try:
        post = Post.query.filter_by(slug=slug).first_or_404()
        user_uuid = request.cookies.get('tph_uuid')
        
        if not user_uuid or user_uuid != post.owner_uuid:
            return jsonify({'error': 'Access Denied'}), 403
        
        # Удаляем пост
        db.session.delete(post)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Post deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/edit/<slug>', methods=['GET', 'POST'])
def edit_post(slug):
    try:
        post = Post.query.filter_by(slug=slug).first_or_404()
        if request.cookies.get('tph_uuid') != post.owner_uuid:
            return jsonify({'error': 'Access Denied'}), 403
        
        if request.method == 'POST':
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.json
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            content = data.get('content', '')
            
            # Обрабатываем видео ссылки
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, content)
            
            for url in urls:
                if is_video_url(url):
                    embed_code = convert_video_url_to_embed(url)
                    if embed_code:
                        content = content.replace(url, embed_code)
            
            post.title = data.get('title')
            post.author_name = data.get('author_name')
            # Bleach очищает HTML, но сохраняет содержимое code/pre блоков как текст
            # HTML теги внутри code/pre уже экранированы через textContent в JavaScript
            post.content = bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=False)
            db.session.commit()
            return jsonify({'slug': post.slug})
        
        return render_template('editor.html', post=post)
    except Exception as e:
        db.session.rollback()
        if request.method == 'POST':
            return jsonify({'error': str(e)}), 500
        raise

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get('PORT', '5032'))
    host = os.environ.get('HOST', '127.0.0.1')
    debug = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    print(f"🚀 Запуск Post приложения на {host}:{port}")
    print(f"🌐 Приложение будет доступно на https://post.dreampartners.online")
    
    app.run(host=host, port=port, debug=debug)

