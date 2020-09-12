
from django.core.files.storage import FileSystemStorage


from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.core import mail

import os
import shutil
# from file_management.file_management_functions import create_folder, file_input, send_results, delete_inputs


def file_input(request,htmlInput,file_folder):
    uploaded_file = request.FILES[htmlInput]
    fs = FileSystemStorage()
    file_path = os.path.join(file_folder,uploaded_file.name)
    name = fs.save(file_path, uploaded_file)
    return(name)

def create_folder(target_dir, function_name):
    fileCount=len(os.listdir(target_dir))
    folder_name = str(fileCount)+'_'+function_name
    return(folder_name)

# function name is a string that will be added on email
# output_path is the path of the file to be attached
def send_results(function_name,request,output_path):

    ## send email
    email_subject = function_name + ' results'
    email_text = 'please find enclosed results of ' + function_name
    sender = 'drmis.tools@gmail.com'
    recipient = [request.POST['user_recipient']]
    bcc =[]
    reply_to=[]
    headers={}
    email = EmailMessage(
        email_subject,
        email_text,
        sender,
        recipient,
        bcc,
        reply_to,
        headers
    )
    email.attach_file(output_path)
    email.send()

def delete_inputs(file_folder,out_file_folder):
    #delete input and output files
    shutil.rmtree(file_folder)
    shutil.rmtree(out_file_folder)

# from file_management.file_management_functions import create_folder, file_input, send_results
