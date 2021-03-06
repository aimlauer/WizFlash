from . import routes
from flask import (
    render_template,
    redirect,
    url_for,
    request,
    current_app,
    session
)
from .bbcode_parser import parser
from forms import ContactForm, CommentForm
from models import (
    db,
    Post,
    Tag,
    Category,
    Comment,
)
from .auth.upload import GenerateFilename
import os
import strgen
import datetime
from youtube_transcript_api import YouTubeTranscriptApi
from werkzeug.security import generate_password_hash as genph
import bbcode


@routes.route('/')
@routes.route('/index')
def home():
    # Orden descending
    news = Post.query.order_by(Post.created_date.desc()).limit(25)

    posts = db.session.query(Post)
    fijados = posts.filter(
        Post.categories.any(Category.category_name == 'Fijados')
    ).order_by(Post.created_date.desc()).all()
    # destacados = Post.query.order_by(Post.views.desc()).limit(10)

    return render_template(
        'home.html',
        nbar='directory',
        news=news,
        fijados=fijados,
        bbcode=bbcode
    )


@routes.route('/aboutus', methods=['GET'])
def aboutus():
    return render_template('aboutus.html')


@routes.route('/tor', methods=['GET'])
def tor():
    return render_template('tor.html')


@routes.route('/c/<name>', methods=['GET', 'POST'])
def category(name=None):
    posts = db.session.query(Post)

    # Esta fue una consulta dificil
    posts = posts.filter(
        Post.categories.any(Category.category_name == name)
    ).order_by(Post.created_date.desc()).all()

    return render_template(
        'category.html',
        posts=posts,
        bbcode=bbcode,
        category_name=name
    )


@routes.route('/search', methods=['GET', 'POST'])
def search():
    # posts_category = Category.query.filter_by(category_name=name).limit(20)
    query = request.args.get('q')
    # Acá tenemos una lista de los tags a buscar, y queremos obtener
    tags = query.split(' ')

    # https://stackoverflow.com/questions/26270927/flask-sqlalchemy-query-many-to-many-tagging-with-multiple-requred-tags
    q = db.session.query(Post)
    for tag in tags:
        q = q.filter(Post.tags.any(Tag.tag_name.contains(tag)))

    search_result = q.all()

    return render_template(
        'search.html',
        query=query,
        search_result=search_result
    )


@routes.route('/view/<id>', methods=['GET', 'POST'])
def view(id=None):
    form = CommentForm()

    password = session.get('password', None)
    if not password:
        session['password'] = strgen.StringGenerator("[\\d\\w]{50}").render()

    comment_password = session['password']
    form.password.data = comment_password

    post = Post.query.get_or_404(id)
    '''
        post.desc =
        regex.sub(r'(?<!//.+)->', '.', line)
        var cite = />>(.*?)->/g;
    '''
    comments = Comment.query.filter_by(
        post_id=id
    )

    post.views += 1
    db.session.commit()

    category = Category.query.filter_by(post_id=id).first()
    if category is None:
        return redirect(
            url_for(
                'routes.output',
                msg="Cuando creaste el post \
                pusiste una categoría que ahora no existe."
            )
        )

    if form.validate_on_submit():
        print(form.file.data)

        # Quiero el nombre del archivo para obtener la extensión,
        # pero no voy a usar el nombre del archivo para identificarlo
        file_data = GenerateFilename(
            form.file.data.filename
        ) if (
            form.file.data is not None
        ) else {'name': '', 'ext': ''}

        new_comment = Comment(
            post_id=id,
            comment=form.comment.data,
            hash_password=genph(form.password.data),
            subject=form.subject.data,
            created_date=datetime.datetime.utcnow(),
            filename=file_data['name'],
            file_ext=file_data['ext']
        )

        db.session.add(new_comment)
        db.session.commit()

        post.total_comments += 1
        db.session.commit()

        file = form.file.data

        if file is not None:
            file.save(os.path.join(
                current_app.config['UPLOAD_FOLDER'],
                'images', file_data['name']
            ))

        return redirect(
            url_for(
                'routes.view',
                id=id
            )
        )

    return render_template(
            'view.html',
            post=post,
            category=category.category.name,
            form=form,
            bbcode=bbcode,
            parser=parser,
            comments=comments
    )


@routes.route('/rules', methods=['GET'])
def rules():
    return render_template('rules.html')


@routes.route('/helpme', methods=['GET'])
def services():
    return render_template('helpme.html', sidebar='services')


@routes.route('/globalmsgs', methods=['GET'])
def globalmsgs():
    return render_template('global.html')


@routes.route('/contact/', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    print(form.errors)

    print(form.errors)
    print('Estoy acá1')
    if form.validate_on_submit():
        print('Estoy acá2')
        return redirect(url_for('routes.register_success'))
    # Si falla vuelve a la misma página con los
    # errores que se produjeron al intentar enviar el formulario
    return render_template('contact.html', sidebar='contact', form=form)


@routes.route('/faq', methods=['GET'])
def faq():
    return render_template('faq.html')


@routes.route('/output/<msg>')
def output(msg='Hola'):
    return render_template(
        'output.html',
        msg=msg
    )


@routes.route('/video/id/<videoId>')
def video(videoId=None):
    transcript = YouTubeTranscriptApi.get_transcript(videoId)

    '''
        print(transcript.video_id,
            transcript.language,
            transcript.language_code,
            whether it has been manually created or generated by YouTube
            transcript.is_generated,
            whether this transcript can be translated or not
            transcript.is_translatable,
            a list of languages the transcript can be translated to
            transcript.translation_languages
        )
        Get info from a video curl using Google API
        "https://www.googleapis.com/youtube/v3/videos?key=AIzaSyDsb4vxGfNEUHLVrHhNFXUCRhEnQDqqy3s
        &part={id,snippet,statistics,status,topicDetails}&id=JL295OjIBtE"
        Part is the most import variable of the query
    '''

    output = ''
    for line in transcript:
        output += 'alguien dijo <span style="color: red;">' + line['text'] \
            + '</span> en el minuto ' + str(line['start']) + '<br/>'

    return 'YouTube: <p>{}</p>'.format(output)
