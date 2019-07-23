"""Creates csv, pdf, xls files"""
from ast import literal_eval
from export_workers.create_messages import (
    create_dict_message,
    message_for_queue
)

from export_workers.rabbitmq_setup import CHANNEL
from files import (
    xls_file,
    csv_file,
    pdf_file,
    create_file_name
)
from get_titles import GetTitles
from requests_to_services import SendRequest

from serializers.job_schema import JobSchema
from export_workers.workers.config.base_config import Config
import export_workers.delete_files

FILE_MAKERS = {
    'xls': xls_file,
    'csv': csv_file,
    'pdf': pdf_file
}

print(1111111111)
def get_answers_for_form(answers):
    """
    Gets users responses from the database
    :param answers: answers
    returns answers for entire form.
    :return: dictionary : Returns dictionary.
    Keys are user, values are dictionaries
    with field and reply for this field.
    """
    answers_list = answers.json()
    users_answers = {answer['user_id']: {} for answer in answers_list}
    get_titles = GetTitles()
    field_title = get_titles.get_field_title(answers_list)
    print(field_title)
    for answer in answers_list:
        title = field_title[answer['field_id']]
        users_answers[answer['user_id']][title] = answer['reply']
    return users_answers


def create_file(channel, method, properties, job_data):
    # pylint: disable=unused-argument
    """
    Callback starts executing when appears task for processing in queue
    :param method: method
    :param properties: properties
    :param job_data: str: Dictionary with keys (form_id, groups, format) converted to string
    :param
    :return: str: Message with status to export service
    """
    print(job_data)
    job_data = job_data.decode('utf-8')
    job_dict = literal_eval(job_data)
    job_schema = JobSchema()
    job_dict = job_schema.load(job_dict)
    if job_dict.errors:
        message = create_dict_message(job_dict.data, job_dict.errors)
        message_for_queue(message, 'answer_to_export')
        return
    job_dict = job_dict.data
    sender = SendRequest()
    answers = sender.request_to_services(Config.ANSWERS_SERVICE_URL, job_dict)
    answers = get_answers_for_form(answers)
    if not answers:
        message = create_dict_message(job_dict, "Answers does not exist")
        message_for_queue(message, "answer_to_export")
        return
    get_title = GetTitles()
    if job_dict['groups']:
        group_response = sender.request_to_services(Config.GROUP_SERVICE_URL, job_dict)
        groups_title = get_title.get_group_titles(group_response)
    else:
        groups_title = ''
    forms_response = sender.request_to_form_service(Config.FORM_SERVICE_URL, job_dict)
    print(type(forms_response))
    form_title = get_title.get_form_title(forms_response)
    file_name = create_file_name(form_title, groups_title)
    export_format = job_dict['export_format']
    status = FILE_MAKERS[export_format](answers, file_name)
    print(status)
    if not status:
        message = create_dict_message(job_dict, 'Something went wrong! File is not created!')
        message_for_queue(message, "answer_to_export")
        return
    job_dict.update({'file_name': file_name})
    message_for_queue(job_dict, 'upload_on_google_drive')

print(123123123123123123131231231231313123123123123131231231231232131231)
CHANNEL.basic_consume(queue='export', on_message_callback=create_file, auto_ack=True)
CHANNEL.start_consuming()
