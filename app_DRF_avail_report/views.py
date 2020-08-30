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
import csv
import os
import shutil

def dict_from_csv(file_path):
    with open(file_path, 'r') as f:
        reader = csv.reader(f, skipinitialspace=True, delimiter=',')
        next(reader)
        result = {}
        for row in reader:
            key = row[0]
            result[key] = row[1]
    return result

def list_from_csv(file_path):
    with open(file_path, 'r') as f:
        reader = csv.reader(f, skipinitialspace=True, delimiter=',')
        next(reader)
        list = []
        for row in reader:
            list.append(row[0])
    return list

def dict_str_to_float(dict):
    for k, v in dict.items():
        dict[k] = float(v)
    return dict

def dict_str_to_int(dict):
    for k, v in dict.items():
        dict[k] = int(v)
    return dict

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

def create_availability_report(vor_tactical_mpo_disposition,ie36,zeiw29,target_dir):
    vor_tactical_mpo_disposition = vor_tactical_mpo_disposition[['Equipment Number', 'Equip. Object Type', 'Maintenance plant', 'User & Info Statuses']]
    vor_tactical_mpo_disposition.columns = ['equipment_number', 'equipment_object_type', 'maintenance_plant1', 'user_info_statuses']

    ie36 = ie36[['Equipment', 'Description', 'Vehicle Type', 'Allocation Code']]
    ie36.columns = ['equipment_number', 'description', 'equipment_object_type', 'allocation_code']

    zeiw29 = zeiw29[['Equipment', 'Notification']]
    zeiw29.columns = ['equipment_number', 'notification']
    datestr1 = datetime.now().strftime('%y%m%d')
    datetime_object = datetime.strptime(datestr1, '%y%m%d')
    datestr2 = datetime_object.strftime('%d %b %y')
    output_dir = target_dir

    df1 = pd.merge(vor_tactical_mpo_disposition, ie36, left_on=['equipment_number', 'equipment_object_type'], \
               right_on=['equipment_number', 'equipment_object_type'], how='left')
    df1 = pd.merge(df1, zeiw29.drop_duplicates(subset=['equipment_number']), left_on='equipment_number', \
               right_on='equipment_number', how='left')

    df3 = df1
    df3['service_status'] = 'In Service'
    df3.loc[(df3['allocation_code'].str.contains('M')) | \
            (df3['description'].str.contains('HARD TARGET')) | \
            (df3['user_info_statuses'].str.contains('|'.join(disposal_user_status_code_list))), 'service_status'] = \
        'Disposal'
    df3.loc[df3['allocation_code'] == 'HX', 'service_status'] = 'Reference'

    # map weapon system IDs, NP & DRF key fleets and platforms to equipment object types
    df3['weapon_system_id'] = df3['equipment_object_type'].map(weapon_system_id_dict)
    df3['np_drf_key_fleet'] = df3['equipment_object_type'].map(np_drf_key_fleet_dict)
    df3['platform'] = df3['equipment_object_type'].map(platform_dict)
    df3['maintenance_plant2'] = df3['maintenance_plant1'].apply(str).map(maintenance_plant_dict)

    # create 'disposition' column containing plant if eqpt is in service and disposal status otherwise
    df3['disposition'] = df3['maintenance_plant2']
    df3.loc[(df3['notification'] > 0), 'disposition'] = '202 WD'
    df3.loc[(df3['service_status'] == 'Disposal'), 'disposition'] = 'Disposal'
    df3.loc[(df3['service_status'] == 'Reference'), 'disposition'] = 'Reference'

    # group by weapon system ID, NP & DRF key fleet, platform and disposition, and calculate quantities
    df4 = pd.DataFrame({'quantity': df3.groupby(['weapon_system_id', 'np_drf_key_fleet', 'platform', \
                                                 'disposition']).size()}).reset_index()

    table1 = pd.pivot_table(df4, values='quantity', index=['weapon_system_id', 'np_drf_key_fleet', 'platform'],columns=['disposition'], fill_value=0).reset_index()
    table1['inventory'] = table1.sum(axis=1)
    table1['in_service'] = table1['inventory'] - table1['Disposal']
    table1['#_available'] = table1[['CA', 'CJOC', 'MPC', 'RCAF', 'RCN', 'VCDS', 'Reference']].sum(axis=1)
    table1['#_unavailable'] = table1[['202 WD', 'ADM (Mat)']].sum(axis=1)
    table1['%_available'] = (100 * table1['#_available'] / table1['in_service']).round(1)
    table1['%_unavailable'] = (100 * table1['#_unavailable'] / table1['in_service']).round(1)
    table1['%_planned'] = table1['platform'].map(availability_target_dict)
    table1['#_planned'] = (table1['%_planned'] * table1['in_service'] / 100).astype('int')
    table2 = table1.groupby(['np_drf_key_fleet']).sum().reset_index()
    table2 = table2[['np_drf_key_fleet', '#_available', '#_planned', 'in_service', 'Disposal']]
    column_sums = table1.select_dtypes(include='int').sum(axis=0)
    column_averages = table1.select_dtypes(include='float').mean(axis=0).round(1)
    table1.loc['Sum'] = column_sums
    table1.loc['Average'] = column_averages


    filename2 = output_dir + '/%s-dglepm-availability-report.xlsx' % datestr1
    writer = pd.ExcelWriter(filename2, engine='xlsxwriter')
    table1.to_excel(writer, sheet_name='Sheet1', startrow=2, index=False)
    df3.to_excel(writer, sheet_name='Sheet2', index=False)
    table2.to_excel(writer, sheet_name='Sheet3', index=False)

    # initialize generic variables
    workbook = writer.book
    worksheet1 = writer.sheets['Sheet1']
    worksheet2 = writer.sheets['Sheet2']

    # initialize formatting variables
    integer_fmt = workbook.add_format({'text_wrap': True})
    percentage_fmt = workbook.add_format({'text_wrap': True, 'num_format': '0.0"%"'})
    bold_fmt = workbook.add_format({'bold': 1})
    bold_align_center_fmt = workbook.add_format({'bold': 1, 'align': 'center'})
    align_right_fmt = workbook.add_format({'align': 'right'})
    bg_color_grey_fmt = workbook.add_format({'bg_color': '#C0C0C0'})
    all_borders_fmt = workbook.add_format({'bottom': 1, 'top': 1, 'left': 1, 'right': 1})
    top_border_fmt = workbook.add_format({'top': 1})
    bottom_border_fmt = workbook.add_format({'bottom': 1})
    left_border_fmt = workbook.add_format({'left': 1})
    right_border_fmt = workbook.add_format({'right': 1})
    underline_fmt = workbook.add_format({'underline': 1})
    font_size_8_fmt = workbook.add_format({'font_size': 8})
    underline_and_font_size_8_fmt = workbook.add_format({'underline': 1, 'font_size': 8})
    italic_and_font_size_8_fmt = workbook.add_format({'italic': 1, 'font_size': 8})
    red_fmt = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    index_fmt = workbook.add_format({'bold': 1, 'align': 'center', 'valign': 'top'})

    # apply formatting to Sheet1
    worksheet1.set_column('A:A', 24)
    worksheet1.set_column('B:B', 40)
    worksheet1.set_column('C:C', 16)
    worksheet1.set_column('D:F', 16, integer_fmt)
    worksheet1.set_column('G:G', 16, percentage_fmt)
    worksheet1.set_column('H:H', 16, integer_fmt)
    worksheet1.set_column('I:O', 12, integer_fmt)
    worksheet1.set_column('P:P', 16, percentage_fmt)
    worksheet1.set_column('Q:Q', 16, integer_fmt)
    worksheet1.set_column('R:S', 12, integer_fmt)
    worksheet1.set_column('T:T', 16, percentage_fmt)
    worksheet1.set_column('U:U', 16, integer_fmt)
    # worksheet1.conditional_format('C5:V22', {'type': 'no_blanks', 'format': align_right_fmt})
    # worksheet1.conditional_format('H3:M20', {'type': 'no_blanks', 'format': bg_color_grey_fmt})
    # worksheet1.conditional_format('P3:R20', {'type': 'no_blanks', 'format': bg_color_grey_fmt})
    # worksheet1.conditional_format('U3:U20', {'type': 'no_blanks', 'format': bg_color_grey_fmt})
    # worksheet1.conditional_format('A21:V22', {'type': 'no_blanks', 'format': bg_color_grey_fmt})
    worksheet1.conditional_format('A3:U24', {'type': 'no_blanks', 'format': all_borders_fmt})
    worksheet1.conditional_format('I1:O1', {'type': 'no_blanks', 'format': all_borders_fmt})
    worksheet1.conditional_format('R1:S1', {'type': 'no_blanks', 'format': all_borders_fmt})
    # worksheet1.conditional_format('A5:B20', {'type': 'no_blanks', 'format': bold_align_center_fmt})
    worksheet1.write(0, 0, 'DGLEPM Availability Report', bold_fmt)
    worksheet1.write(1, 0, 'As of %s' % datestr2)
    worksheet1.conditional_format('P4', {'type': 'cell', 'criteria': '<', 'value': '$G$4', 'format': red_fmt})
    worksheet1.conditional_format('P5', {'type': 'cell', 'criteria': '<', 'value': '$G$5', 'format': red_fmt})
    worksheet1.conditional_format('P6', {'type': 'cell', 'criteria': '<', 'value': '$G$6', 'format': red_fmt})
    worksheet1.conditional_format('P7', {'type': 'cell', 'criteria': '<', 'value': '$G$7', 'format': red_fmt})
    worksheet1.conditional_format('P8', {'type': 'cell', 'criteria': '<', 'value': '$G$8', 'format': red_fmt})
    worksheet1.conditional_format('P9', {'type': 'cell', 'criteria': '<', 'value': '$G$9', 'format': red_fmt})
    worksheet1.conditional_format('P10', {'type': 'cell', 'criteria': '<', 'value': '$G$10', 'format': red_fmt})
    worksheet1.conditional_format('P11', {'type': 'cell', 'criteria': '<', 'value': '$G$11', 'format': red_fmt})
    worksheet1.conditional_format('P12', {'type': 'cell', 'criteria': '<', 'value': '$G$12', 'format': red_fmt})
    worksheet1.conditional_format('P13', {'type': 'cell', 'criteria': '<', 'value': '$G$13', 'format': red_fmt})
    worksheet1.conditional_format('P14', {'type': 'cell', 'criteria': '<', 'value': '$G$14', 'format': red_fmt})
    worksheet1.conditional_format('P15', {'type': 'cell', 'criteria': '<', 'value': '$G$15', 'format': red_fmt})
    worksheet1.conditional_format('P16', {'type': 'cell', 'criteria': '<', 'value': '$G$16', 'format': red_fmt})
    worksheet1.conditional_format('P17', {'type': 'cell', 'criteria': '<', 'value': '$G$17', 'format': red_fmt})
    worksheet1.conditional_format('P18', {'type': 'cell', 'criteria': '<', 'value': '$G$18', 'format': red_fmt})
    worksheet1.conditional_format('P19', {'type': 'cell', 'criteria': '<', 'value': '$G$19', 'format': red_fmt})
    worksheet1.conditional_format('P20', {'type': 'cell', 'criteria': '<', 'value': '$G$20', 'format': red_fmt})
    worksheet1.conditional_format('P21', {'type': 'cell', 'criteria': '<', 'value': '$G$21', 'format': red_fmt})
    worksheet1.conditional_format('P22', {'type': 'cell', 'criteria': '<', 'value': '$G$22', 'format': red_fmt})
    worksheet1.conditional_format('P24', {'type': 'cell', 'criteria': '<', 'value': '$G$24', 'format': red_fmt})
    worksheet1.conditional_format('Q4', {'type': 'cell', 'criteria': '<', 'value': '$H$4', 'format': red_fmt})
    worksheet1.conditional_format('Q5', {'type': 'cell', 'criteria': '<', 'value': '$H$5', 'format': red_fmt})
    worksheet1.conditional_format('Q6', {'type': 'cell', 'criteria': '<', 'value': '$H$6', 'format': red_fmt})
    worksheet1.conditional_format('Q7', {'type': 'cell', 'criteria': '<', 'value': '$H$7', 'format': red_fmt})
    worksheet1.conditional_format('Q8', {'type': 'cell', 'criteria': '<', 'value': '$H$8', 'format': red_fmt})
    worksheet1.conditional_format('Q9', {'type': 'cell', 'criteria': '<', 'value': '$H$9', 'format': red_fmt})
    worksheet1.conditional_format('Q10', {'type': 'cell', 'criteria': '<', 'value': '$H$10', 'format': red_fmt})
    worksheet1.conditional_format('Q11', {'type': 'cell', 'criteria': '<', 'value': '$H$11', 'format': red_fmt})
    worksheet1.conditional_format('Q12', {'type': 'cell', 'criteria': '<', 'value': '$H$12', 'format': red_fmt})
    worksheet1.conditional_format('Q13', {'type': 'cell', 'criteria': '<', 'value': '$H$13', 'format': red_fmt})
    worksheet1.conditional_format('Q14', {'type': 'cell', 'criteria': '<', 'value': '$H$14', 'format': red_fmt})
    worksheet1.conditional_format('Q15', {'type': 'cell', 'criteria': '<', 'value': '$H$15', 'format': red_fmt})
    worksheet1.conditional_format('Q16', {'type': 'cell', 'criteria': '<', 'value': '$H$16', 'format': red_fmt})
    worksheet1.conditional_format('Q17', {'type': 'cell', 'criteria': '<', 'value': '$H$17', 'format': red_fmt})
    worksheet1.conditional_format('Q18', {'type': 'cell', 'criteria': '<', 'value': '$H$18', 'format': red_fmt})
    worksheet1.conditional_format('Q19', {'type': 'cell', 'criteria': '<', 'value': '$H$19', 'format': red_fmt})
    worksheet1.conditional_format('Q20', {'type': 'cell', 'criteria': '<', 'value': '$H$20', 'format': red_fmt})
    worksheet1.conditional_format('Q21', {'type': 'cell', 'criteria': '<', 'value': '$H$21', 'format': red_fmt})
    worksheet1.conditional_format('Q22', {'type': 'cell', 'criteria': '<', 'value': '$H$22', 'format': red_fmt})
    worksheet1.conditional_format('Q23', {'type': 'cell', 'criteria': '<', 'value': '$H$23', 'format': red_fmt})
    worksheet1.write(22, 2, 'Sum', bold_align_center_fmt)
    worksheet1.write(23, 2, 'Average', bold_align_center_fmt)
    worksheet1.write(23, 3, '-')
    worksheet1.write(23, 4, '-')
    worksheet1.write(23, 5, '-')
    worksheet1.write(22, 6, '-')
    worksheet1.write(23, 7, '-')
    worksheet1.write(23, 8, '-')
    worksheet1.write(23, 9, '-')
    worksheet1.write(23, 10, '-')
    worksheet1.write(23, 11, '-')
    worksheet1.write(23, 12, '-')
    worksheet1.write(23, 13, '-')
    worksheet1.write(23, 14, '-')
    worksheet1.write(22, 15, '-')
    worksheet1.write(23, 16, '-')
    worksheet1.write(23, 17, '-')
    worksheet1.write(23, 18, '-')
    worksheet1.write(22, 19, '-')
    worksheet1.write(23, 20, '-')
    worksheet1.merge_range('I2:O2', 'Available [6]', bold_align_center_fmt)
    worksheet1.merge_range('R2:S2', 'Unavailable [9]', bold_align_center_fmt)
    # worksheet1.conditional_format('A20', {'type': 'no_blanks', 'format': bold_align_center_fmt})
    worksheet1.write(24, 0, 'Notes:', underline_and_font_size_8_fmt)
    worksheet1.write(25, 0, '[1] Total eqpt holdings.', font_size_8_fmt)
    worksheet1.write(26, 0, '[2] Eqpt that is awaiting disposal, or has been disposed of, but remains on charge. Includes \
    eqpt where Description field contains “HARD TARGET”, User Status field contains “OBSO” (obsolete), “CBAL” \
    (cannibalization), “MONU” (monument), “NOHT” (non-operational hard target) or “DLTD” (deleted), or Allocation Code \
    field contains “M”.', font_size_8_fmt)
    worksheet1.write(27, 0, '[3] Eqpt that is in service. Calculated as: Total − Disposal.', font_size_8_fmt)
    worksheet1.write(28, 0, '[4] Target availability percentages designated by DGLEPM.', font_size_8_fmt)
    worksheet1.write(29, 0, '[5] Calculated as: Planned Availability * In Service.', font_size_8_fmt)
    worksheet1.write(30, 0, '[6] Eqpt that is held by a FG/FE L1, regardless of serviceability.', font_size_8_fmt)
    worksheet1.write(31, 0, '[7] Calculated as: CA + RCAF + RCN + CJOC + VCDS + MPC.', font_size_8_fmt)
    worksheet1.write(32, 0, '[8] Calculated as: 100 * Total Available / In Service.', font_size_8_fmt)
    worksheet1.write(33, 0, '[9] Eqpt that is held by ADM (Mat), or is undergoing 3rd/4th line maintenance at 202 WD or \
    industry. Includes eqpt with outstanding or in process notifications under Planning Plant 0001 (202 WD).', font_size_8_fmt)
    worksheet1.write(34, 0, '[10] Calculated as: ADM (Mat) + 202 WD.', font_size_8_fmt)
    worksheet1.write(35, 0, '[11] Calculated as: 100 * Total Unavailable / In Service.', font_size_8_fmt)
    worksheet1.write(36, 0, 'Caveats:', underline_and_font_size_8_fmt)
    worksheet1.write(37, 0, '1. Does not yet account for eqpt that is unavailable due to lack of furnished spares. Working \
    on devising methodology.', font_size_8_fmt)
    # worksheet1.conditional_format('A39:M39', {'type': 'no_blanks', 'format': top_border_fmt})
    # worksheet1.conditional_format('A41:M41', {'type': 'no_blanks', 'format': bottom_border_fmt})
    # worksheet1.conditional_format('A39:A41', {'type': 'no_blanks', 'format': left_border_fmt})
    # worksheet1.conditional_format('K39:K41', {'type': 'no_blanks', 'format': right_border_fmt})
    worksheet1.set_landscape()
    worksheet1.set_paper(5)
    worksheet1.fit_to_pages(1, 1)

    # Save report
    writer.save()
    return(filename2)




# load required constants
TOOL_DATA_DIR = os.path.join(os.path.join(BASE_DIR,'app_DRF_avail_report'),'tool_data')
weapon_system_id_dict = dict_from_csv(os.path.join(TOOL_DATA_DIR, 'weapon_system_id_dict.csv')) #
np_drf_key_fleet_dict = dict_from_csv(os.path.join(TOOL_DATA_DIR, 'np_drf_key_fleet_dict.csv')) #
platform_dict = dict_from_csv(os.path.join(TOOL_DATA_DIR,'platform_dict.csv')) #
maintenance_plant_dict = dict_from_csv(os.path.join(TOOL_DATA_DIR, 'maintenance_plant_dict.csv')) #
availability_target_dict = dict_from_csv(os.path.join(TOOL_DATA_DIR,'availability_target_dict.csv')) #
disposal_user_status_code_list = list_from_csv(os.path.join(TOOL_DATA_DIR,'disposal_user_status_code_list.csv'))
availability_target_dict = dict_str_to_float(availability_target_dict)

# vor_tactical_mpo_disposition_filename = 'input_data/vor_tactical_mpo_disposition.csv'
# ie36_filename = 'input_data/ie36.csv'
# zeiw29_filename = 'input_data/zeiw29.csv'

# def availability_report(vor_tac, ie36file, zeiw29file):

def DRF_Report(request):
    if request.method == 'POST':

        function_name = 'DRF_avail_report'
        #input files directory
        folder_name = create_folder(INPUT_DIR,function_name)
        file_folder = os.path.join(INPUT_DIR,folder_name)
        os.makedirs(file_folder)

        #save input files and read them as pandas dataframes
        vor_tactical_mpo_disposition_filename = file_input(request,'vor_tac',file_folder)
        ie36_filename = file_input(request,'ie36_input',file_folder)
        zeiw29_filename = file_input(request,'zeiw29_input',file_folder)
        vor_tactical_mpo_disposition = pd.read_csv(vor_tactical_mpo_disposition_filename, encoding = "ISO-8859-1", engine='python')
        ie36 = pd.read_csv(ie36_filename, encoding = "ISO-8859-1", engine='python')
        zeiw29 = pd.read_csv(zeiw29_filename, encoding = "ISO-8859-1", engine='python')

        #output files directory
        out_folder_name = create_folder(OUTPUT_DIR,function_name)
        out_file_folder = os.path.join(OUTPUT_DIR,folder_name)
        os.makedirs(out_file_folder)

        ###do stuff with input files
        output_file = create_availability_report(vor_tactical_mpo_disposition,ie36,zeiw29,out_file_folder)
        ###

        #save output file
        output_path = os.path.join(out_file_folder,'result.csv')
        # df2.to_csv(output_path)

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
        email.attach_file(output_file)
        email.send()

        #delete input and output files
        # shutil.rmtree(file_folder)
        # shutil.rmtree(out_file_folder)

    return render(request,'DRF_report.html')
