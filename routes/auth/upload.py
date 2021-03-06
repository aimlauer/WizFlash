from .. import routes
from flask import (
    render_template,
    redirect,
    url_for,
    current_app,
    request,
    session
)
import strgen
from forms import (
    UploadForm,
    DeleteForm,
    ThankPostForm,
    ThankUserForm,
    DeleteCommentForm,
    CreateCategoryForm
)
from models import (
    db,
    Thank,
    User,
    Post,
    Comment,
    CategoryList,
    Category,
    Tag,
    FilePost
)
from werkzeug.security import check_password_hash as checkph
from werkzeug.security import generate_password_hash as genph

import datetime
import os
from werkzeug.utils import secure_filename
# from werkzeug.datastructures import FileStorage
from flask_login import (
    current_user,
    login_required,
)

# from youtube_transcript_api import YouTubeTranscriptApi


@routes.route('/thanks/post/<id>', methods=['GET', 'POST'])
@login_required
def thanks_post(id=None):
    form = ThankPostForm()
    print(form.errors)

    if form.is_submitted():
        print("submitted")

    print(form.errors)

    if form.validate_on_submit():
        post = Post.query.get(id)
        thanked = Thank.query.filter_by(
            user_id=current_user.id,
            post_id=post.id
        ).first()

        if thanked is not None:
            return redirect(
                url_for(
                    'routes.output',
                    msg="""Ya agradeciste este post!"""
                )
            )

        post.total_thanks += 1
        new_thank = Thank(
            user_id=current_user.id,
            post_id=post.id,
        )
        db.session.add(new_thank)
        db.session.commit()

        return redirect(url_for('routes.view', id=post.id))
    return render_template('thanks.html', form=form)


@routes.route('/thanks/user/<id>', methods=['GET', 'POST'])
def thanks_user(id=None):
    form = ThankUserForm()
    print(form.errors)

    if form.is_submitted():
        print("submitted")

    # if form.validate():
    #   print("valid")

    print(form.errors)
    if form.validate_on_submit():
        user = User.query.get(id)
        user.karma += 1

        db.session.commit()
        return redirect(url_for('routes.show_user', username=user.username))

    return render_template('thanks.html', form=form)


@routes.route('/delete/post/<id>', methods=['GET', 'POST'])
def delete(id=None):
    form = DeleteForm()
    print(form.errors)

    if form.is_submitted():
        print("submitted")

    print(form.errors)
    print('Estoy acá1')

    if form.validate_on_submit():
        post = Post.query.get(id)
        if checkph(post.hash_password, form.password.data) \
           or (current_user.is_authenticated and current_user.admin == 1):
            db.session.delete(post)
            db.session.commit()
        else:
            return redirect(
                url_for(
                    'routes.output',
                    msg="""Contraseña errónea, bro."""
                )
            )

        return redirect(url_for('routes.index'))
        # Ahora debería guardar el catalogo del negocio en la db

    return render_template('user/delete.html', form=form)


@routes.route('/delete/comment/<id>', methods=['GET', 'POST'])
def delete_comment(id=None):
    form = DeleteCommentForm()

    post_id = request.args.get("id")
    if form.validate_on_submit():
        comment = Comment.query.get(id)
        if checkph(comment.hash_password, form.password.data):
            post = Post.query.get(post_id)
            post.total_comments -= 1
            db.session.delete(comment)
            db.session.commit()

            return redirect(url_for('routes.view', id=post_id))
            # Ahora debería guardar el catalogo del negocio en la db
        else:
            return redirect(
                url_for(
                    'routes.output',
                    msg="""Contraseña errónea, bro."""
                )
            )

    return render_template('user/delete.html', form=form)


'''
        @routes.route('/categories', methods=['GET', 'POST'])
        def categories():
            lista_categorias = CategoryList.query.all()
            print(lista_categorias)
            return render_template(
                'truehome.html',
                lista_categorias=lista_categorias,
                nbar='categories'
            )
'''


@routes.route('/categories', methods=['GET'])
def misc():
    lista_categorias = CategoryList.query.all()

    password = session.get('password', None)
    if not password:
        session['password'] = strgen.StringGenerator("[\\d\\w]{50}").render()

    print(lista_categorias)
    return render_template(
        'misc.html',
        lista_categorias=lista_categorias,
        nbar='categories'
    )


@routes.route('/createcategory', methods=['GET', 'POST'])
def createcategory():
    form = CreateCategoryForm()

    # if current_user.admin:
    if form.validate_on_submit():
        new_category = CategoryList(
            name=form.category.data,
            desc=form.desc.data
        )
        db.session.add(new_category)
        db.session.commit()
        return redirect(url_for('routes.index'))
    '''
    else:
        return redirect(
                    url_for(
                        'routes.output',
                        msg="""No podés crear una
                        categoría porque no sos administrador."""
                    )
                )
    '''

    return render_template('user/createcategory.html', form=form)


def GenerateFilename(formfilesdatafilename):
    # Quiero el nombre del archivo para obtener la extensión,
    # pero no voy a usar el nombre del archivo para identificarlo
    filename = secure_filename(formfilesdatafilename)

    extension = filename.split('.').pop()
    # Voy a guardar el archivo con un nombre random.
    filename = strgen.StringGenerator("[\\d\\w]{20}").render()
    filename += '.'+extension
    return {'name': filename, 'ext': extension}


@routes.route('/upload', methods=['GET', 'POST'])
def upload():
    form = UploadForm()
    password = session.get('password', None)
    if not password:
        session['password'] = strgen.StringGenerator("[\\d\\w]{50}").render()
    post_password = session['password']
    form.password.data = post_password

    lista_categorias = CategoryList.query.all()

    # Hacerlo de una forma más pythonica o como quiera que se diga.
    Categorias = [('', "Elegir Categoría")]
    for c in lista_categorias:
        Categorias.append((c.name, c.name.title()))
    form.category.choices = Categorias

    print(form.errors)

    if form.validate_on_submit():

        # ¿Existe la categoría a la que intentás agregar un post?
        # Pensarlo mejor
        c = CategoryList.query.filter_by(name=form.category.data).first()
        if c is None:
            return redirect(
                url_for(
                    'routes.output',
                    msg='No existe esa categoría'
                )
            )

        # Quiero el nombre del archivo para obtener la extensión,
        # pero no voy a usar el nombre del archivo para identificarlo
        file_data = GenerateFilename(form.files.data.filename)

        print("Vamos a intentar guardarlo \
              como {}".format(file_data['name']))

        # Compruebo que no esté usado.
        name_used = FilePost.query.filter_by(file=file_data['name']).first()
        # Si está usado generá otro hasta que no lo esté.
        print('Name_used vale %s' % name_used)
        while (name_used is not None):
            file_data = GenerateFilename(form.files.data.filename)

            name_used = FilePost.query.filter_by(
                file=file_data['name']
            ).first()
            print("El nombre del archivo estaba \
                  usado voy a usar este {}\
                  en su lugar". format(file_data['name']))

        # Ahora debería guardar el catalogo del negocio en la db
        new_post = Post(
            subject=form.subject.data,
            desc=form.desc.data,
            # Crear el thumbnail pequeño
            thumbnail=file_data['name'],
            hash_password=genph(form.password.data),
            thumbnail_max=file_data['name'],
            # tags = form.tags.data,
            # cambiar a category
            created_date=datetime.datetime.utcnow(),
            views=0,
            total_comments=0,
            total_thanks=0,
            hidden=False,
        )
        db.session.add(new_post)
        db.session.commit()

        file = form.files.data

        file.save(os.path.join(
            current_app.config['UPLOAD_FOLDER'], 'images', file_data['name']
        ))

        new_post_files = FilePost(
            post_id=new_post.id,
            file=file_data['name'],
            extension=file_data['ext']
        )
        db.session.add(new_post_files)
        db.session.commit()

        # Agrego una categoría al post, si no existe no deberías poder
        # agregar un post a una categoría inexistente
        new_post_category = Category(
            category=c,
            post_id=new_post.id
        )

        db.session.add(new_post_category)
        db.session.commit()

        tags = form.tags.data.split(' ')
        print(tags)

        for tag in tags:
            new_post_tag = Tag(
                tag_name=tag,
            )
            new_post.tags.append(new_post_tag)

        db.session.commit()

        return redirect(url_for('routes.view', id=new_post.id))

    return render_template(
        'upload.html',
        nbar='upload',
        form=form,
        lista_categorias=lista_categorias
    )
