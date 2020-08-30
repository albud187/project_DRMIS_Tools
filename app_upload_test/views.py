from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, CreateView
from django.core.files.storage import FileSystemStorage
from django.urls import reverse_lazy

from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.core import mail

from datetime import datetime
import pandas as pd
import numpy as np

import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR,'files_input')
OUTPUT_DIR =os.path.join(BASE_DIR,'files_output')

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

def UploadTestView(request):
    if request.method == 'POST':

        function_name = 'upload_test'
        #input files directory
        folder_name = create_folder(INPUT_DIR,function_name)
        file_folder = os.path.join(INPUT_DIR,folder_name)
        os.makedirs(file_folder)

        #save input files
        file1 = file_input(request,'document1',file_folder)

        #output files directory
        out_folder_name = create_folder(OUTPUT_DIR,function_name)
        out_file_folder = os.path.join(OUTPUT_DIR,folder_name)
        os.makedirs(out_file_folder)

        ###do stuff with input files
        df=pd.read_csv(file1)
        df2 = df*2
        ###

        #save output file
        output_path = os.path.join(out_file_folder,'result.csv')
        df2.to_csv(output_path)

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

        #delete input and output files
        # shutil.rmtree(file_folder)
        # shutil.rmtree(out_file_folder)

    return render(request,'upload_test.html')
