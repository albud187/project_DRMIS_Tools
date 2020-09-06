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
from file_management.file_management_functions import create_folder, file_input, send_results, delete_inputs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR,'files_input')
OUTPUT_DIR =os.path.join(BASE_DIR,'files_output')

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
        send_results(function_name,request,output_path)

        #delete input and output files
        # delete_inputs(file_folder,out_file_folder)
        # shutil.rmtree(file_folder)
        # shutil.rmtree(out_file_folder)

    return render(request,'upload_test.html')
