def generate_views(compute_function,
                   classname,
                   outfile,
                   filename_template,
                   menu_function,
                   filename_models,
                   login):

    filename_models = filename_models.strip(".py")
    compute_function_name = compute_function.__name__
    compute_function_file = compute_function.__module__

    if menu_function:
        menu_function_name = menu_function.__name__
        menu_function_file = menu_function.__module__
        menu = True
    else:
        menu = False

    import inspect
    arg_names = inspect.getargspec(compute_function).args
    defaults  = inspect.getargspec(compute_function).defaults

    # Add code for file upload only if it is strictly needed
    file_upload = False

    if menu:
        # FIXME: This should be replaced by a good regex
        filetxt = ("widget='file'", 'widget="file"',
                   "widget = 'file'", 'widget = "file"')
        menutxt = open(menu_function_file + ".py", 'r').read()
        for txt in filetxt:
            if txt in menutxt:
                file_upload = True
                break
    else:
        for name in arg_names:
            if 'filename' in name:
                file_upload = True
                break

    code = '''\
from django.shortcuts import render_to_response
from django.template import RequestContext
from %(filename_models)s import %(classname)s, %(classname)sForm
''' % vars()
    if login:
        code += '''\
from %(filename_models)s import %(classname)sUser
from %(filename_models)s import %(classname)sUserForm
from forms import CreateNewLoginForm, LoginForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect
''' % vars()
    code += '''\
from %(compute_function_file)s import %(compute_function_name)s as compute_function
''' % vars()

    if menu:
        code += '''
# Menu object
from %(menu_function_file)s import %(menu_function_name)s as menu_function
menu = menu_function()
''' % vars()

    if file_upload:
        code += '''
import os
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.isdir(UPLOAD_DIR):
    os.mkdir(UPLOAD_DIR)
'''

    code += '''
def index(request):
    result = None
'''
    if login:
        code += '''\
    user = request.user
'''
    if file_upload and menu:
        if login:
            code += '''
    form = %(classname)sForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':

        # User is logged in
        if request.user.is_authenticated():
            data = request.POST.copy()
            data['user'] = user.id
            form = %(classname)sUserForm(data)
            if form.is_valid():
                for field in form:
                    name = %(classname)s._meta.get_field(field.name).verbose_name.strip()
                    value = field.data
                    if field.name in request.FILES:
                        filename = field.data.name
                        data_item = menu.set_value(name, filename)
                        with open(os.path.join(UPLOAD_DIR, filename), 'wb+') as destination:
                            for chunk in field.data.chunks():
                                destination.write(chunk)
                    else:
                        if field.name not in ("user", "result", "comments"):
                            data_item = menu.set_value(name, value)

                f = form.save(commit=False)
                result = compute(menu)
                if user.email:
                    user.email_user("Computations Complete", """\
A simulation has been completed. Please log in at

http://localhost:8000/login

to see the results.""")

                # Save to db
                f.result = result
                f.save()

        # Anonymous user
        else:
            if form.is_valid():
                for field in form:
                    name = %(classname)s._meta.get_field(field.name).verbose_name.strip()
                    value = field.data
                    if field.name in request.FILES:
                        filename = field.data.name
                        menu.set_value(name, filename)
                        with open(os.path.join(UPLOAD_DIR, filename), 'wb+') as destination:
                            for chunk in field.data.chunks():
                                destination.write(chunk)
                    else:
                        menu.set_value(name, value)

                result = compute(menu)

        form = %(classname)sForm(request.POST, request.FILES)

    else:
        # Retrieve previous result and input if user is logged in
        if request.user.is_authenticated():

            # FIXME: Find out why this fails when there are no objects
            # and find a better way to deal with the error.
            try:
                objects = %(classname)sUser.objects.filter(user=user)
                if len(objects) > 0:
                    # Negative indexing not allowed.
                    instance = objects[len(objects)-1]
                    form = %(classname)sForm(instance=instance)
                    result = instance.result
            except:
                pass

''' % vars()
        else:
            code += '''
    form = %(classname)sForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        for field in form:
            name = %(classname)s._meta.get_field(field.name).verbose_name.strip()
            value = field.data
            if field.name in request.FILES:
                filename = field.data.name
                menu.set_value(name, filename)
                with open(os.path.join(UPLOAD_DIR, filename), 'wb+') as destination:
                    for chunk in field.data.chunks():
                        destination.write(chunk)
            else:
                menu.set_value(name, value)
        result = compute(menu)
        form = %(classname)sForm(request.POST, request.FILES)
''' % vars()

    elif file_upload and not menu:
        if login:
            code += '''
    filename = None
    form = %(classname)sForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':

        # User is logged in
        if request.user.is_authenticated():
            data = request.POST.copy()
            data['user'] = user.id
            form = %(classname)sUserForm(data)
            if form.is_valid():
                for field in form:
                    if field.name in request.FILES:
                        filename = field.data.name
                        with open(os.path.join(UPLOAD_DIR, filename), 'wb+') as destination:
                            for chunk in field.data.chunks():
                                destination.write(chunk)
                f = form.save(commit=False)
                result = compute(f)
                if user.email:
                    user.email_user("Computations Complete", """\
A simulation has been completed. Please log in at

http://localhost:8000/login

to see the results.""")

                # Save to db
                f.result = result
                f.save()

        # Anonymous user
        else:
            #form = %(classname)sForm(request.POST or None, request.FILES or None)
            if form.is_valid():
                for field in form:
                    if field.name in request.FILES:
                        filename = field.data.name
                        with open(os.path.join(UPLOAD_DIR, filename), 'wb+') as destination:
                            for chunk in field.data.chunks():
                                destination.write(chunk)
                form = form.save(commit=False)
                request.session["filename"] = filename
                result = compute(form, request)

        form = %(classname)sForm(request.POST, request.FILES)

    else:
        # Retrieve previous result and input if user is logged in
        if request.user.is_authenticated():

            # FIXME: Find out why this fails when there are no objects
            # and find a better way to deal with the error.
            try:
                objects = %(classname)sUser.objects.filter(user=user)
                if len(objects) > 0:
                    # Negative indexing not allowed.
                    instance = objects[len(objects)-1]
                    form = %(classname)sForm(instance=instance)
                    result = instance.result
            except:
                pass

''' % vars()

        else:
            code += '''
    filename = None
    form = %(classname)sForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        for field in form:
            if field.name in request.FILES:
                filename = field.data.name
                with open(os.path.join(UPLOAD_DIR, filename), 'wb+') as destination:
                    for chunk in field.data.chunks():
                        destination.write(chunk)
        form = form.save(commit=False)
        request.session["filename"] = filename
        result = compute(form, request)
        form = %(classname)sForm(request.POST, request.FILES)
''' % vars()

    elif not file_upload and menu:
        if login:
            code += '''
    form = %(classname)sForm(request.POST or None)
    if request.method == 'POST':

        # User is logged in
        if request.user.is_authenticated():
            data = request.POST.copy()
            data['user'] = user.id
            form = %(classname)sUserForm(data)
            if form.is_valid():
                for field in form:
                    if field.name not in ("user", "result", "comments"):
                        name = %(classname)s._meta.get_field(field.name).verbose_name.strip()
                        value = field.data
                        menu.set_value(name, value)
                f = form.save(commit=False)
                result = compute(menu)
                if user.email:
                    user.email_user("Computations Complete", """\
A simulation has been completed. Please log in at

http://localhost:8000/login

to see the results.""")

                # Save to db
                f.result = result
                f.save()

        # Anonymous user
        else:
            if form.is_valid():
                for field in form:
                    name = %(classname)s._meta.get_field(field.name).verbose_name.strip()
                    value = field.data
                    menu.set_value(name, value)
                result = compute(menu)

        form = %(classname)sForm(request.POST, request.FILES)

    else:
        # Retrieve previous result and input if user is logged in
        if request.user.is_authenticated():

            # FIXME: Find out why this fails when there are no objects
            # and find a better way to deal with the error.
            try:
                objects = %(classname)sUser.objects.filter(user=user)
                if len(objects) > 0:
                    # Negative indexing not allowed.
                    instance = objects[len(objects)-1]
                    form = %(classname)sForm(instance=instance)
                    result = instance.result
            except:
                pass

''' % vars()

        else:
            code += '''
    form = %(classname)sForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        for field in form:
            name = %(classname)s._meta.get_field(field.name).verbose_name.strip()
            value = field.data
            menu.set_value(name, value)
        result = compute(menu)
        form = %(classname)sForm(request.POST)
''' % vars()

    else:
        if login:
            code += '''
    form = %(classname)sForm(request.POST or None)
    if request.method == 'POST':

        # User is logged in
        if request.user.is_authenticated():
            data = request.POST.copy()
            data['user'] = user.id
            form = %(classname)sUserForm(data)
            if form.is_valid():
                f = form.save(commit=False)
                result = compute(f)
                if user.email:
                    user.email_user("Computations Complete", """\
A simulation has been completed. Please log in at

http://localhost:8000/login

to see the results.""")

                # Save to db
                f.result = result
                f.save()

        # Anonymous user
        else:
            if form.is_valid():
                result = compute(form)

        form = %(classname)sForm(request.POST, request.FILES)

    else:
        # Retrieve previous result and input if user is logged in
        if request.user.is_authenticated():

            # FIXME: Find out why this fails when there are no objects
            # and find a better way to deal with the error.
            try:
                objects = %(classname)sUser.objects.filter(user=user)
                if len(objects) > 0:
                    # Negative indexing not allowed.
                    instance = objects[len(objects)-1]
                    form = %(classname)sForm(instance=instance)
                    result = instance.result
            except:
                pass

''' % vars()

        else:
            code += '''
    form = %(classname)sForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form = form.save(commit=False)
        result = compute(form)
        form = %(classname)sForm(request.POST or None)
''' % vars()

    code += '''
    return render_to_response(
        "%(filename_template)s",
        {"form": form,
         "result": result,
''' % vars()
    if login:
        code += '''\
         "user": user,
'''
    code += '''
        },
        context_instance=RequestContext(request))
''' % vars()

    if menu:
        code += '''
def compute(menu):
    """
    Generic function for calling compute_function with values
    taken from the menu object.
    Return the output from the compute_function.
    """

    # compute_function must have only one positional argument
    # named menu
    import inspect
    arg_names = inspect.getargspec(compute_function).args
    if len(arg_names) == 1 and arg_names[0] == "menu":
        result = compute_function(menu)
    else:
        raise TypeError('%s(%s) can only have one argument named "menu"'
                        % (compute_function_name, ', '.join(arg_names)))
    return result
'''

    else:
        if file_upload:
            code += '''
def compute(form, request):
'''
        else:
            code += '''
def compute(form):
'''
        code += '''
    """
    Generic function for compute_function with arguments
    taken from a form object (django.forms.ModelForm subclass).
    Return the output from the compute_function.
    """
    # Extract arguments to the compute function
    import inspect
    arg_names = inspect.getargspec(compute_function).args
'''

        if file_upload:
            code += '''

    form_data = []
    for name in arg_names:
        if name != "filename":
            if hasattr(form, name):
                form_data.append(getattr(form, name))
        else:
            form_data.append(request.session.get("filename"))
'''
        else:
            code += '''

    # Extract values from form
    form_data = [getattr(form, name) for name in arg_names
                 if hasattr(form, name)]
'''

        # Give a warning and insert helper code if positional
        # arguments because the user must then convert form_data
        # elements explicitly.
        import inspect
        arg_names = inspect.getargspec(compute_function).args
        defaults  = inspect.getargspec(compute_function).defaults
        if defaults is not None and len(defaults) != len(arg_names):
            # Insert example on argument conversion since there are
            # positional arguments where default_field might be the
            # wrong type
            code += '''
    # Convert data to right types (if necessary)
    # for i in range(len(form_data)):
    #    name = arg_names[i]
    #    if name == '...':
    #         form_data[i] = int(form_data[i])
    #    elif name == '...':
'''
        else:
            # We have default values: do right conversions
            code += '''
    defaults  = inspect.getargspec(compute_function).defaults

    # Make defaults as long as arg_names so we can traverse both with zip
    if defaults:
        defaults = ["none"]*(len(arg_names)-len(defaults)) + list(defaults)
    else:
        defaults = ["none"]*len(arg_names)

    # Convert form data to the right type:
    import numpy
    for i in range(len(form_data)):
        if defaults[i] != "none":
            #if isinstance(defaults[i], (str,bool,int,float)): # bool not ready
            if isinstance(defaults[i], (str,int,float)):
                pass  # special widgets for these types do the conversion
            elif isinstance(defaults[i], numpy.ndarray):
                form_data[i] = numpy.array(eval(form_data[i]))
            elif defaults[i] is None:
                if form_data[i] == 'None':
                    form_data[i] = None
                else:
                    try:
                        # Try eval if it succeeds...
                        form_data[i] = eval(form_data[i])
                    except:
                        pass # Just keep the text
            else:
                # Use eval to convert to right type (hopefully)
                try:
                    form_data[i] = eval(form_data[i])
                except:
                    print 'Could not convert text %s to %s for argument %s' % (form_data[i], type(defaults[i]), arg_names[i])
                    print 'when calling the compute function...'
'''

        code += '''
    # Run computations
    result = compute_function(*form_data)
    return result
''' % vars()

    if login:
        code += '''
def add_comment(request):
    if request.method == 'POST':
        try:
            objects = %(classname)sUser.objects.filter(user=request.user)
            if len(objects) > 0:
                instance = objects[len(objects)-1]
                instance.delete()
                form = %(classname)sUserForm(instance=instance)
                f = form.save(commit=False)
                f.comments = request.POST.get("comments", None)
                f.save()
                form = %(classname)sForm(instance=instance)
                result = instance.result
        except:
            pass
    return HttpResponseRedirect("/")

def create_login(request):
    """
    Create a login for a new user.
    """
    form = CreateNewLoginForm()
    if request.POST:
        form = CreateNewLoginForm(request.POST)
        if form.is_valid():
            newuser = User()
            username = form.cleaned_data['username']
            pw = form.cleaned_data['password']
            newuser.username = username
            newuser.set_password(pw)
            newuser.email = form.cleaned_data['email']
            newuser.save()
            user = authenticate(username=username, password=pw)
            login(request, user)
            return HttpResponseRedirect('/')

    return render_to_response('reg.html', {'form' : form},
            context_instance=RequestContext(request))

def login_func(request):
    form = LoginForm()
    if request.POST:
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)

            if user:
                if user.is_authenticated():
                    if user.is_active:
                        login(request, user)
                        return HttpResponseRedirect('/')
                    else:
                        return HttpRespose("Account disabled")
                else:
                    return HttpResponse("Invalid login")
            else:
                return HttpResponse("Invalid login")
    return render_to_response("login.html", {'form' : form},
            context_instance=RequestContext(request))

def logout_func(request):
    logout(request)
    return HttpResponseRedirect('/')

def old(request):
    forms = []
    results = []
    if request.user.is_authenticated():
        user = request.user
        try:
            objects = %(classname)sUser.objects.filter(user=user)
            counter = len(objects) - 1
            while counter >= 0:
                instance = objects[counter]
                forms.append(%(classname)sForm(instance=instance))
                result = instance.result
                if instance.comments:
                    result += "<h3>Comments</h3>" + instance.comments
                results.append(result)
                counter -= 1
        except:
            pass

    data = zip(forms, results)
    return render_to_response("old.html",
            {"forms": forms,
             "results": results},
            context_instance=RequestContext(request))
''' % vars()

    if outfile is None:
        return code
    else:
        out = open(outfile, 'w')
        out.write(code)
        out.close()
