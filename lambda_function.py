# -*- coding: utf-8 -*-

# This is a simple Hello World Alexa Skill, built using
# the implementation of handler classes approach in skill builder.
import logging
import boto3
import os

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.ui import SimpleCard
from ask_sdk_model import Response

sb = SkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# lambda environment variable
bucket =  os.environ['Bucket'] 

# memory dump filename
raw_file = "windows-memory.raw"

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = "Hello."

        handler_input.response_builder.speak(speech_text).set_card(
            SimpleCard("Hello World", speech_text)).set_should_end_session(
            False)
        return handler_input.response_builder.response


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = "You can say hello to me!"

        handler_input.response_builder.speak(speech_text).ask(
            speech_text).set_card(SimpleCard(
                "Hello World", speech_text))
        return handler_input.response_builder.response


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = "Goodbye!"

        handler_input.response_builder.speak(speech_text).set_card(
            SimpleCard("Hello World", speech_text))
        return handler_input.response_builder.response


class FallbackIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speech_text = (
            "The Hello World skill can't help you with that.  "
            "You can say hello!!")
        reprompt = "You can say hello!!"
        handler_input.response_builder.speak(speech_text).ask(reprompt)
        return handler_input.response_builder.response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speech = "Sorry, there was some problem. Please try again!!"
        handler_input.response_builder.speak(speech).ask(speech)

        return handler_input.response_builder.response


###################################
###       Custom Skill         ####
###       Capture Tim's Memory ####
###################################

class CaptureMemoryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("CaptureMemoryIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        """
        This function will download a memory dump exe from S3,
        run it, and upload the dump to S3; ready for your awesome 
        forensics skills.
        """
        speech_text = ""
        
        ec2 = boto3.resource('ec2', region_name='us-west-2')
        ssm_client = boto3.client('ssm')
        
        slots = handler_input.request_envelope.request.intent.slots
        server = slots["server"].value

        host_list = [instance.id for instance in ec2.instances.all() for name in instance.tags if name["Key"] == "Name" if name["Value"].lower() == server.lower()]
        if len(host_list) > 0:
            for hosts in host_list:
                ec2_instance = ec2.Instance(hosts)
                platform = ec2_instance.platform
                state = ec2_instance.state['Name']
                if state == "running":
                    instance_ids = [hosts]
                    if platform == "windows":
                        commands = [f"aws s3 cp s3://{bucket}/tools/winpmem_1.6.2.exe C:\\Windows\\Temp", 
                        "cd C:\\Windows\\Temp", 
                        f".\winpmem_1.6.2.exe {raw_file}", 
                        f"aws s3 cp {raw_file} s3://{bucket}/evidence/"]
                        resp = ssm_client.send_command(DocumentName="AWS-RunPowerShellScript", Parameters={'commands': commands}, InstanceIds=instance_ids)
                        speech_text = "Tim's memory has been captured?"
                    else:
                        speech_text = f"{server} is not a Window's hosts. Please see the next tutorial?"
                else:
                    speech_text = f"{server} is offline."
        else:
            speech_text = "Unable to locate server or servers."
        handler_input.response_builder.speak(speech_text).set_card(SimpleCard("Hi", speech_text)).set_should_end_session(True)
        return handler_input.response_builder.response
        

##################################
###       Skillbuilder        ####
##################################

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_exception_handler(CatchAllExceptionHandler())

# custom
sb.add_request_handler(CaptureMemoryIntentHandler())

# handler
lambda_handler = sb.lambda_handler()