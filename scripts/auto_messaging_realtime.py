import base64
import datetime
import enum
import logging
import os
import re
import json
from threading import Timer

import gradio as gr
import requests

from modules import scripts, script_callbacks
from modules.processing import StableDiffusionProcessingTxt2Img
from modules.scripts import PostprocessImageArgs

# from gpiozero import CPUTemperature

# cpu = CPUTemperature()
# print(cpu.temperature)
# log = logging.getLogger("[auto-messaging-realtime]")
log = logging.getLogger("[auto-messaging-realtime]")


class RepeatingTimer(Timer):
    def run(self):
        self.finished.wait(self.interval)
        while not self.finished.is_set():
            self.function(*self.args, **self.kwargs)
            self.finished.wait(self.interval)


class EnumSendImageResult(enum.Enum):
    ALL = 'SD-Image-All'
    ONLY_GRID = 'Grid-Image-only'
    NO_GRID = 'Each-Image-noGrid'

    @classmethod
    def values(cls):
        return [e.value for e in cls]


class EnumSendContent(enum.Enum):
    SDIMAGE = 'SD-Image'
    # ScreenShot = 'ScreenShot' # for the developer, if u know what you do, u can enable this by yourself.
    TextPrompt = 'Text-Prompt'
    Text_neg_prompt = 'Text-negPrompt'
    PNG_INFO = 'PNG-INFO(max 4096 characters)'
    SD_INFO = 'SD-INFO(max 4096 characters)'
    Text_Temperature = 'Text-Temperature'

    @classmethod
    def values(cls):
        return [e.value for e in cls]


class EnumTriggetType(enum.Enum):
    SDIMAGE = 'SD-Image-generated'
    TIMER = 'Timer-Countdown'
    STATE_TEMPERATURE_GPU = 'STATE-Temperature-GPU '
    STATE_TEMPERATURE_CPU = 'STATE-Temperature-CPU'

    @classmethod
    def to_dict(cls):
        return {e.name: e.value for e in cls}

    @classmethod
    def items(cls):
        return [(e.name, e.value) for e in cls]

    @classmethod
    def keys(cls):
        return [e.name for e in cls]

    @classmethod
    def values(cls):
        return [e.value for e in cls]


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def read_from_file(filename):
    with open(filename, "r", encoding="utf8") as file:
        return json.load(file)


def write_to_file(filename, current_ui_settings):
    with open(filename, "w", encoding="utf8") as file:
        json.dump(current_ui_settings, file, indent=4, ensure_ascii=False)


def community_export_to_text(*args, **kwargs):
    dictx = (dict(zip(args_keys, args)))
    out = json.dumps(dictx, indent=2)
    write_to_file('Auto-MSG-settings.json', dictx)
    return out


def community_import_from_text(*args, **kwargs):
    try:
        if len(str(args[0])) <= 0:
            jo = read_from_file('Auto-MSG-settings.json')
        else:
            jo = json.loads(args[0])
        import_data = []
        for ele in args_keys:
            import_data.append(jo[ele])
        log.warning("[O][Auto-LLM][Import-OK]")
        return import_data
    except Exception as e:
        log.warning("[X][Auto-LLM][Import-Fail]")


def tel_getupdate(im_telegram_token_botid):
    url = f'https://api.telegram.org/bot{im_telegram_token_botid}/getUpdates'
    result = requests.post(url)
    return result.text


def update_temperature_label(celsius):
    fahrenheit = round((celsius * 1.8) + 32, 1)
    result = f" {celsius}°C/{fahrenheit}°F"
    log.warning(f"[][][update_temperature_label]result: {result}")
    # self.bot_line_notify_trigger_by_temperature.info = result
    return result


class AutoMessaging(scripts.Script):

    def __init__(self) -> None:
        self.lin_notify_history_array = [['', '', '']]
        self.telegram_bot_history_array = [['', '', '']]
        self.discord_bot_history_array = [['', '', '']]
        self.timer_count_threading = None

    def title(self):
        return "Auto Msg RealTime"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def timer_cancel(self):
        log.warning(f"[][Timer][canceling]")
        if not (self.timer_count_threading is None):
            self.timer_count_threading.cancel()
            log.warning(f"[][Timer][canceled]")

    def timer(self, setting__im_line_notify_enabled, setting__im_telegram_enabled,
              setting_trigger_type, setting_image_count, setting_time_count,
              setting_temperature,
              setting_send_content_with,
              im_line_notify_token, im_line_notify_msg_header,
              im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
              setup_enum_send_image_result_radio):
        if setting_time_count > 0:
            if EnumTriggetType.TIMER.value in setting_trigger_type:
                if not (self.timer_count_threading is None):
                    self.timer_count_threading.cancel()
                    log.warning(f"[][Timer][canceled]@{setting_time_count} secs")
                self.timer_count_threading = RepeatTimer(setting_time_count, self.send_msg_all_lets_go,
                                                         [setting__im_line_notify_enabled,
                                                          setting__im_telegram_enabled,
                                                          setting_trigger_type, setting_image_count,
                                                          setting_time_count,
                                                          setting_temperature,
                                                          setting_send_content_with,
                                                          im_line_notify_token, im_line_notify_msg_header,
                                                          im_telegram_token_botid, im_telegram_token_chatid,
                                                          im_telegram_msg_header,
                                                          setup_enum_send_image_result_radio])
                self.timer_count_threading.start()
                log.warning(f"[][Timer][Start] countdown @{setting_time_count} secs")
            else:
                log.warning(
                    f"[][Timer][result_line_notify]: {setting_trigger_type} {EnumTriggetType.TIMER} has not check @{setting_time_count} secs")

        else:
            log.warning(f"[][Timer][setting_time_count] <0 @{setting_time_count} secs")
            self.timer_count_threading.cancel()

    def send_msg_all_from_processing(self, p, setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                     setting_trigger_type, setting_image_count, setting_time_count,
                                     setting_temperature_gpu, setting_temperature_cpu, setting_send_content_with,
                                     im_line_notify_token, im_line_notify_msg_header,
                                     im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                                     setup_enum_send_image_result_radio,
                                     setting__im_discord_enabled, im_discord_token_botid,
                                     im_discord_token_chatid, im_discord_msg_header, im_discord_notify_history):

        if EnumSendContent.TextPrompt.value in setting_send_content_with:
            im_line_notify_msg_header += '\n▣prompt:' + p.prompt
            im_telegram_msg_header += '\n▣prompt:' + p.prompt
            im_discord_msg_header += '\n▣prompt:' + p.prompt

        if EnumSendContent.Text_neg_prompt.value in setting_send_content_with:
            im_line_notify_msg_header += '\n▣neg-prompt:' + p.negative_prompt
            im_telegram_msg_header += '\n▣neg-prompt:' + p.negative_prompt
            im_discord_msg_header += '\n▣neg-prompt:' + p.negative_prompt

        self.send_msg_all_lets_go(setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                  setting_trigger_type, setting_image_count, setting_time_count,
                                  setting_temperature_gpu, setting_temperature_cpu, setting_send_content_with,
                                  im_line_notify_token, im_line_notify_msg_header,
                                  im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                                  setup_enum_send_image_result_radio,
                                  setting__im_discord_enabled, im_discord_token_botid,
                                  im_discord_token_chatid, im_discord_msg_header, im_discord_notify_history)

    def button_setting(self, *args):
        return self.send_msg_all_lets_go(*args).get('setting')

    def button_line(self, *args):
        return self.send_msg_all_lets_go(*args).get('line')

    def button_telegram(self, *args):
        return self.send_msg_all_lets_go(*args).get('telegram')

    def button_discord(self, *args):
        return self.send_msg_all_lets_go(*args).get('discord')

    def send_msg_all_lets_go(self, setting__im_line_notify_enabled, setting__im_telegram_enabled,
                             setting_trigger_type, setting_image_count, setting_time_count,
                             setting_temperature_gpu, setting_temperature_cpu, setting_send_content_with,
                             im_line_notify_token, im_line_notify_msg_header,
                             im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                             setup_enum_send_image_result_radio,
                             setting__im_discord_enabled, im_discord_token_botid,
                             im_discord_token_chatid, im_discord_msg_header, im_discord_notify_history):
        opened_files = []
        opened_files_path = []
        up_3_level_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        log.warning(up_3_level_path)

        base_folder = os.path.dirname(__file__)
        global on_image_saved_params
        if on_image_saved_params is not None:
            if EnumSendContent.PNG_INFO.value in setting_send_content_with:
                for ele in on_image_saved_params:
                    im_line_notify_msg_header += '\n▣ImgFile-Info:' + str(ele.filename)
                    im_telegram_msg_header += '\n▣ImgFile-Info:' + str(ele.filename)
                    im_discord_msg_header += '\n▣ImgFile-Info:' + str(ele.filename)
            if EnumSendContent.SD_INFO.value in setting_send_content_with:
                for ele in on_image_saved_params:
                    im_line_notify_msg_header += '\n▣SD-Info:' + str(ele.pnginfo)
                    im_telegram_msg_header += '\n▣SD-Info:' + str(ele.pnginfo)
                    im_discord_msg_header += '\n▣SD-Info:' + str(ele.pnginfo)

            if EnumSendImageResult.ONLY_GRID.value in setup_enum_send_image_result_radio:
                if len(on_image_saved_params) > 1:
                    while len(on_image_saved_params) > 1:
                        on_image_saved_params.pop(0)
            elif EnumSendImageResult.NO_GRID.value in setup_enum_send_image_result_radio:
                if len(on_image_saved_params) > 1:
                    on_image_saved_params.pop()

            for ele in on_image_saved_params:
                # image_path = os.path.join(base_folder, "..", "..", "..", ele.filename)
                image_path = os.path.join(up_3_level_path, ele.filename)
                image = open(image_path, 'rb')
                opened_files.append(image)
                opened_files_path.append(image_path)
            on_image_saved_params = []

        # for the developer, if u know what you do, u can enable this by yourself.
        # if EnumSendContent.ScreenShot.value in setting_send_content_with:
        #     myscreenshot = pyautogui.screenshot()
        #     image_path = os.path.join(base_folder, "..", "myScreenshot.png")
        #     myscreenshot.save(image_path)
        #     image = open(image_path, 'rb')
        #     opened_files.append(image)

        if setting__im_line_notify_enabled:
            result_line_notify = self.send_msg_linenotify(opened_files, im_line_notify_token, im_line_notify_msg_header)
            log.warning(f"[][send_msg_all][result_line_notify]: {result_line_notify}")

        if setting__im_telegram_enabled:
            result_telegram_bot = self.send_msg_telegram(opened_files, im_telegram_token_botid,
                                                         im_telegram_token_chatid,
                                                         im_telegram_msg_header)
            log.warning(f"[][send_msg_all][result_telegram_bot]: {result_telegram_bot}")
        if setting__im_discord_enabled:
            result_discord_bot = self.send_msg_discord(opened_files, opened_files_path, im_discord_token_botid,
                                                       im_discord_token_chatid,
                                                       im_discord_msg_header)
            log.warning(f"[][send_msg_all][result_discord_bot]: {result_discord_bot}")

        return {'setting': [self.lin_notify_history_array[0], self.telegram_bot_history_array[0],
                            self.discord_bot_history_array[0]],
                'line': self.lin_notify_history_array,
                'telegram': self.telegram_bot_history_array,
                'discord': self.discord_bot_history_array}

    def send_msg_discord(self, opened_files, opened_files_path, im_discord_token_botid, im_discord_token_chatid,
                         im_discord_msg_header):
        # https://discord.com/developers/docs/resources/message
        im_discord_token_botid = str(im_discord_token_botid or '').strip()
        im_discord_token_chatid = str(im_discord_token_chatid or '').strip()
        im_discord_msg_header = str(im_discord_msg_header or '').strip()
        log.warning(
            f"[][starting][send_msg_discord]: {im_discord_token_botid, im_discord_token_chatid, im_discord_msg_header}")
        #https://www.postman.com/discord-api/discord-api/request/gf0s32j/create-message
        #https://discord.com/developers/docs/reference
        # url = f"https://discordapp.com/api/channels/{im_discord_token_chatid}/messages"
        # url = f"https://discord.com/api/v9/channels/{im_discord_token_chatid}/messages"
        url = f"https://discord.com/api/v10/channels/{im_discord_token_chatid}/messages"

        # headers = {
        #     'Content-Type': 'application/json',
        #     'Accept': 'application/json'
        # }
        payload = {}
        result = ''

        if len(opened_files_path) > 0:
            headers = {"Authorization": 'Bot ' + im_discord_token_botid,
                       # "Content-Disposition": """form-data; name="payload_json" """,
                       # "Content-Type": "application/json",
                       # "Content-Type": "image/png",
                       # "Content-Type": 'multipart/form-data'
                       # "Content-Type": 'application/x-www-form-urlencoded'
                       }
            payload = {"content": im_discord_msg_header,  #https://discord.com/developers/docs/reference#uploading-files
                       "message_reference": {
                           "message_id": "233648473390448641"
                       },
                       # 'embeds':[],
                       # 'attachments':[],
                       # "attachments": [{
                       #    "id": 0,
                       #    "description": "Image of a cute little cat",
                       #    "filename": "myfilename.png"
                       # }, {
                       #    "id": 1,
                       #    "description": "Rickroll gif",
                       #    "filename": "mygif.gif"
                       # }]
                       }
            json_arr = []
            img_seek_0_obj = {}
            for index, img_path in enumerate(opened_files_path):
                filename = os.path.basename(img_path)
                # with open(img_path, "rb") as opened_image_file:
                # image_data_base64 = 'data:image/png;base64,' + base64.b64encode(opened_image_file.read()).decode("utf-8")
                # img_seek_0_obj[filename] = opened_image_file.read()

                # img_seek_0 = opened_files[index].seek(0)
                # img_seek_0_obj[filename] = image_data_base64
                #data:image/png;base64,BASE64_ENCODED_JPEG_IMAGE_DATA
                opened_files[index].seek(0)
                img_seek_0_obj[filename] = opened_files[index].read()
                # img.seek(0)
                json_arr.append({
                    "id": index,
                    "description": filename,
                    "filename": filename,
                    "title": filename,
                    "image": {
                        # "url": "https://www.decade.tw/wp-content/uploads/2021/09/DECADE_new.png"
                        "url": "attachment://" + filename
                    },
                    "thumbnail": {
                        "url": "attachment://" + filename
                    },

                }
                )
                # with open(img_path, "rb") as data:
                #     img_data_read_body = data.read()
                # post_data[filename]=img_data_read_body
                # if index is 0:
                #     payload['embeds'][0]['data'] = image_data_base64
                #     payload['embeds'][0]['thumbnail']['url'] = image_data_base64
                #     payload['embeds'][0]['image']['url'] = image_data_base64
            payload['attachments'] = json_arr
            payload['embeds'] = json_arr
            post_json = json.dumps(payload)
            log.warning(f"[][starting][send_msg_discord][post_json]: {post_json}")
            result = requests.post(url, headers=headers, json=post_json, files=img_seek_0_obj)
            log.warning(f"[][][send_msg_discord]w/image: {result}")

            # for index,img in enumerate(opened_files):
            #     img.seek(0)
            #     imagefile = {'imageFile': img}
            #     headers = {"Content-Disposition": f"""form-data; name="files[{index}]"; filename="{opened_files_path[index]}" """,
            #                "Content-Type": "image/png",
            #                }
            #     result = requests.post(url, headers=headers, data=post_json, files=imagefile)

        headers = {"Authorization": 'Bot ' + im_discord_token_botid,
                   "Content-Type": "application/json",
                   # "Content-Type": 'multipart/form-data'
                   # "Content-Type": 'application/x-www-form-urlencoded'
                   }
        payload = {"content": im_discord_msg_header, "tts": 'false'}
        post_json = json.dumps(payload)
        result = requests.post(url, headers=headers, data=post_json).text
        # result = requests.post(url, headers=headers, data=data, files=imagefile)

        self.discord_bot_history_array.append([datetime.datetime.now().__str__(), result, im_discord_msg_header])
        if len(self.discord_bot_history_array) > 3:
            self.discord_bot_history_array.remove(self.discord_bot_history_array[0])

        return self.discord_bot_history_array

    def send_msg_linenotify(self, opened_files, im_line_notify_token, im_line_notify_msg_header):
        im_line_notify_token = str(im_line_notify_token or '').strip()
        im_line_notify_msg_header = str(im_line_notify_msg_header or '').strip()
        log.warning(
            f"[][starting][send_msg_linenotify]: {opened_files, im_line_notify_token, im_line_notify_msg_header}")
        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Authorization': 'Bearer ' + im_line_notify_token
        }
        data = {
            'message': im_line_notify_msg_header
        }
        result = ''
        if len(opened_files) > 0:
            for img in opened_files:
                img.seek(0)
                imagefile = {'imageFile': img}
                result = requests.post(url, headers=headers, data=data, files=imagefile)
                log.warning(f"[][][send_msg_linenotify]w/image: {result}")

        else:
            result = requests.post(url, headers=headers, data=data)
            log.warning(f"[][][send_msg_linenotify]w/text: {result}")

        result = str(result.text)
        self.lin_notify_history_array.append([datetime.datetime.now().__str__(), result, im_line_notify_msg_header])
        if len(self.lin_notify_history_array) > 3:
            self.lin_notify_history_array.remove(self.lin_notify_history_array[0])
        return self.lin_notify_history_array

    def send_msg_telegram(self, opened_files, im_telegram_token_botid, im_telegram_token_chatid,
                          im_telegram_msg_header):
        im_telegram_token_botid = str(im_telegram_token_botid or '').strip()
        im_telegram_token_chatid = str(im_telegram_token_chatid or '').strip()
        im_telegram_msg_header = str(im_telegram_msg_header or '').strip()

        log.warning(
            f"[][starting][send_msg_telegram]: {opened_files, im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header}")

        assert type(im_telegram_msg_header) == str, "must be str"

        # im_telegram_msg_header = trim_string(str(im_telegram_msg_header), 1000, '...(tele img caption max len=4096)')
        # log.warning(f"[1][][send_msg_telegram]im_telegram_msg_header: {im_telegram_msg_header}")
        ori_str = im_telegram_msg_header
        if len(ori_str) > 800:
            log.warning(
                f"[][][send_msg_telegram]img caption too long >800 send append send text alternative: {im_telegram_msg_header}")
            im_telegram_msg_header = "[send from web-ui] Image Caption Too Long; send text msg alternative"
            # im_telegram_msg_header = im_telegram_msg_header[:800]+'...(tele img caption max len=4096)'

        # msg_all = bot_telegram_msg_header + str(bot_line_notify_trigger_by) + str(bot_line_notify_send_with)
        headers = {'Content-Type': 'application/json', "cache-control": "no-cache"}
        result = ''
        # API ref: https://core.telegram.org/bots/api#sendphoto
        if len(opened_files) > 0:
            url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendPhoto'
            data = {"chat_id": im_telegram_token_chatid, "caption": im_telegram_msg_header}
            for img in opened_files:
                img.seek(0)
                imagefile = {'photo': img}
                # result = requests.post(url, headers=headers, data=json.dumps(data), files=imagefile)
                result = requests.post(url, params=data, files=imagefile)
                log.warning(f"[][][send_msg_telegram]w/image: {result}")
            if len(ori_str) > 800:
                url2 = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendMessage'
                data2 = {"chat_id": im_telegram_token_chatid, "text": ori_str}
                log.warning(f"[][][send_msg_telegram]data: {data2}")
                result2 = requests.post(url2, params=data2)
                log.warning(f"[][][send_msg_telegram]w/text: {result2}")

        else:
            # url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendMessage?chat_id={im_telegram_token_chatid}&text={im_telegram_msg_header}'
            # result = requests.get(url)
            url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendMessage'
            data = {"chat_id": im_telegram_token_chatid, "text": im_telegram_msg_header}
            log.warning(f"[][][send_msg_telegram]data: {data}")
            # result = requests.post(url, headers=headers, data=data, json=json.dumps(data))
            result = requests.post(url, params=data)
            log.warning(f"[][][send_msg_telegram]w/text: {result}")

        result = str(result.text)
        self.telegram_bot_history_array.append([datetime.datetime.now().__str__(), result, im_telegram_msg_header])
        if len(self.telegram_bot_history_array) > 3:
            self.telegram_bot_history_array.remove(self.telegram_bot_history_array[0])
        log.warning(f"[][][send_msg_telegram]: {result}")
        return self.telegram_bot_history_array

    def ui(self, is_img2img):
        with gr.Blocks() as gr_blocks:
            # gr.Markdown("Blocks")
            with gr.Accordion(open=False, label="Auto Messaging Realtime v20240808"):
                with gr.Tab("Setting"):
                    setting__im_line_notify_enabled = gr.Checkbox(label=" 0.Enable LINE-Notify", value=False,
                                                                  elem_id="state-auto-msg_setting__im_line_notify_enabled")
                    setting__im_telegram_enabled = gr.Checkbox(label=" 0.Enable Telegram-bot", value=False,
                                                               elem_id="state-auto-msg_setting__im_telegram_enabled")
                    setting__im_discord_enabled = gr.Checkbox(label=" 0.Enable Discord-bot", value=False,
                                                              elem_id="state-auto-msg_setting__im_discord_enabled")

                    setting_trigger_type = gr.CheckboxGroup(
                        EnumTriggetType.values(),
                        value=[EnumTriggetType.values()[0]],
                        label="1. Trigger: IF [[[ XXX ]]] Then YYY",
                        info="When should send? trigger events by XXX?")
                    with gr.Row():
                        setting_image_count = gr.Slider(1, 100, value=1,
                                                        label="2.1 " + EnumTriggetType.SDIMAGE.value + " count",
                                                        step=1,
                                                        info="[" + EnumTriggetType.SDIMAGE.value + "] send msg by generate count",
                                                        elem_id="state-auto-msg_setting_image_count")
                        setting_time_count = gr.Slider(0, 6000, value=60,
                                                       label="2.2  " + EnumTriggetType.TIMER.value,
                                                       step=1,
                                                       info="[" + EnumTriggetType.TIMER.value + "]send by seconds. ",
                                                       elem_id="state-auto-msg_setting_time_count")
                    with gr.Row():
                        setting_temperature_gpu = gr.Slider(0, 100, value=60,
                                                            label="2.3 " + EnumTriggetType.STATE_TEMPERATURE_GPU.value + " limit °C",
                                                            step=1,
                                                            info="[" + EnumTriggetType.STATE_TEMPERATURE_GPU.value + "] 60°C/140°F",
                                                            elem_id="state-auto-msg_setting_temperature_gpu")
                        setting_temperature_cpu = gr.Slider(0, 100, value=60,
                                                            label="2.4 " + EnumTriggetType.STATE_TEMPERATURE_CPU.value + " limit °C",
                                                            step=1,
                                                            info="[" + EnumTriggetType.STATE_TEMPERATURE_CPU.value + "] 60°C/140°F",
                                                            elem_id="state-auto-msg_setting_temperature_cpu")

                    setting_send_content_with = gr.CheckboxGroup(
                        EnumSendContent.values(),
                        value=[EnumSendContent.values()[0]],
                        label="3. IF XXX Then [[[ YYY ]]]",
                        info="Send what? then YYY(send text, image or both)?",
                        elem_id="state-auto-msg_setting_send_content_with")

                    setup_enum_send_image_result_radio = gr.Radio(EnumSendImageResult.values(),
                                                                  value='Grid-Image-only',
                                                                  label="4. IF [Step.3 SD-Image] checked & batch size>1 ; Send which one?",
                                                                  info="Grid-Image-only is recommended",
                                                                  elem_id="state-auto-msg_setup_enum_send_image_result_radio")

                    with gr.Row():
                        setting_timer_start = gr.Button(
                            "Start Timer-Countdown")
                        setting_timer_cancel = gr.Button(
                            "Cancel Timer-Countdown")
                    setting_send_button = gr.Button(
                        "Test Send Message (enabled.)")
                    setting_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="5. History",
                        headers=["TimeStamp", "Response", "Msg"],
                        datatype=["str", "str", "str"],
                        row_count=3,
                        col_count=(3, "fixed"),
                    )
                with gr.Tab("LINE-Notify"):
                    gr.Markdown("* LINE-Notify only need [Token]\n"
                                "* add Notify as friend or add that to group, which don`t need chatID")

                    im_line_notify_token = gr.Textbox(label="1.[im_line_notify_token]", lines=1,
                                                      value="",
                                                      placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                                                      #tcnDSnAR6Gl6pTMBfQ4wOxqtq0eSyXqqJ9Q1Hck4dRO
                                                      elem_id="state-auto-msg_im_line_notify_token"
                                                      )
                    im_line_notify_msg_header = gr.Textbox(label="2. [msg header]", lines=1,
                                                           value="[From web-ui-line-notify]",
                                                           placeholder="[From web-ui-line-notify]",
                                                           elem_id="state-auto-msg_im_line_notify_msg_header"

                                                           )
                    im_line_notify_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="3. History",
                        headers=["TimeStamp", "Response", "Msg"],
                        datatype=["str", "str", "str"],
                        row_count=3,
                        col_count=(3, "fixed"),
                    )
                    im_line_notify_send_button = gr.Button("Test Send (LINE)")
                with gr.Tab("Telegram-bot"):
                    gr.Markdown("* Telegram-bot need [BotToken] and [ChatID ] \n"
                                "* how to get, check: https://github.com/xlinx/sd-webui-decadetw-auto-messaging-realtime")
                    with gr.Row():
                        im_telegram_token_botid = gr.Textbox(label="1.1 [BotToken]", lines=1,
                                                             info="format: xxxx:yyyyyyyy",
                                                             value="",
                                                             placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                                                             elem_id="state-auto-msg_im_telegram_token_botid"
                                                             #7376923093:AAGtCtd9Ogiq9yT1IBsbRD6ENQ5DbAqL6Ig

                                                             )
                        im_telegram_getupdates_result = gr.JSON()
                    im_telegram_getupdates = gr.Button("1.2 Get Token Info: ChatId")

                    with gr.Row():
                        im_telegram_token_chatid = gr.Textbox(label="2.1 [ChatID] ", lines=1,
                                                              info="format:1234567890. can be send to personal or group",
                                                              value="",
                                                              placeholder="XXXXXXXXXX",  #1967680189
                                                              elem_id="state-auto-msg_im_telegram_token_chatid"
                                                              )

                        im_telegram_msg_header = gr.Textbox(label="2.2 [msg header]", lines=1,
                                                            info="append on every message. like prompt or temperature.",
                                                            value="[From web-ui-telegram-bot]",
                                                            placeholder="[From web-ui-telegram-bot]",
                                                            elem_id="state-auto-msg_im_telegram_msg_header"
                                                            )
                    im_telegram_notify_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="3. History",
                        headers=["TimeStamp", "Response", "Msg"],
                        datatype=["str", "str", "str"],
                        row_count=3,
                        col_count=(3, "fixed"),
                    )
                    im_telegram_send_button = gr.Button("Test Send (Telegram)")
                with gr.Tab("Discord-bot"):
                    gr.Markdown("* Discord need [BotToken] and [ChannelID] \n"
                                "* how to get, check: https://github.com/xlinx/sd-webui-decadetw-auto-messaging-realtime")

                    with gr.Row():
                        with gr.Column(scale=5):
                            im_discord_token_botid = gr.Textbox(label="1.1 [BotToken ]", lines=1,
                                                                info="format: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
                                                                value="",
                                                                placeholder="MTI3NDg3MTUzODk4NTczMDA1OQ.GKPcS7.SUwUBEyCby2skYyE08WOukd7xOU9kjVTqalcY8",
                                                                elem_id="state-auto-msg_im_discord_token_botid"
                                                                # MTI3NDg3MTUzODk4NTczMDA1OQ.G7937H.Z-CBE-YIOd4pw_4eQ9G2Bc85BeHIp29cZoUJm8
                                                                # MTI3NDg3MTUzODk4NTczMDA1OQ.GKPcS7.SUwUBEyCby2skYyE08WOukd7xOU9kjVTqalcY8
                                                                )
                        with gr.Column(scale=2):
                            im_discord_token_chatid = gr.Textbox(label="1.2[ChatID]", lines=1,
                                                                 info="format:1234567890. can be send to personal or group",
                                                                 value="1274866471884816395",
                                                                 placeholder="1274866471884816395",
                                                                 elem_id="state-auto-msg_im_discord_token_chatid"
                                                                 #1274866471884816395
                                                                 )

                    im_discord_msg_header = gr.Textbox(label="2 [msg header]", lines=1,
                                                       info="append on every message. like prompt or temperature.",
                                                       value="[From web-ui-discord-bot]",
                                                       placeholder="[From web-ui-discord-bot]",
                                                       elem_id="state-auto-msg_im_discord_msg_header"
                                                       )
                    im_discord_notify_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="3. History",
                        headers=["TimeStamp", "Response", "Msg"],
                        datatype=["str", "str", "str"],
                        row_count=3,
                        col_count=(3, "fixed"),
                    )
                    im_discord_send_button = gr.Button("Test Send (discord)")
                with gr.Tab("Manual"):
                    gr.Markdown(
                        "### Other IM app \n"
                        "* Seems only for business use, I can`t find the way now. IF u know or others IM app, plz let me know. leave command on git. https://github.com/xlinx/sd-webui-decadetw-auto-messaging-realtime")
                    gr.Markdown(
                        "### Trigger manual \n"
                        "* IF [XXX] then [YYY] \n"
                        "* 1 XXX= image (send by every 1-100 image generated) \n"
                        "* 2 XXX= time (send by every seconds. (0 to disable))\n"
                        "* 3 XXX= PC-state (GPU)\n"
                        "* 4 YYY= send text or sd-image \n"
                    )
                    gr.Markdown(
                        "### Max request limit \n"
                        "* Max 1000 request per hour(includes text image), 10MB per file. \n"
                        "* API Rate Limit plz check: https://notify-bot.line.me/doc/en/ | https://core.telegram.org/bots/api\n"
                    )
                with gr.Tab("Export/Import"):
                    gr.Markdown("* Share and see how people how to use LLM in SD.\n"
                                "* Community Share Link: \n"
                                "* https://github.com/xlinx/sd-webui-decadetw-auto-messaging-realtime\n"
                                )
                    with gr.Row():
                        community_export_btn = gr.Button("0. Export&Save setting to text")
                        community_import_btn = gr.Button("0. Import|Load setting")

                    community_text = gr.Textbox(
                        label="1. copy/paste Setting here",
                        lines=3,
                        value="",
                        placeholder="Export&Save first; if here empty will load from disk")
        all_args = [setting__im_line_notify_enabled, setting__im_telegram_enabled,
                    setting_trigger_type, setting_image_count, setting_time_count,
                    setting_temperature_gpu, setting_temperature_cpu, setting_send_content_with,
                    im_line_notify_token, im_line_notify_msg_header,
                    im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header,
                    setup_enum_send_image_result_radio,
                    setting__im_discord_enabled, im_discord_token_botid,
                    im_discord_token_chatid, im_discord_msg_header]

        community_export_btn.click(community_export_to_text,
                                   inputs=all_args,
                                   outputs=[community_text])
        community_import_btn.click(community_import_from_text,
                                   inputs=community_text,
                                   outputs=all_args)
        im_telegram_getupdates.click(tel_getupdate,
                                     inputs=[im_telegram_token_botid],
                                     outputs=[im_telegram_getupdates_result])
        setting_temperature_gpu.change(fn=update_temperature_label,
                                       inputs=[setting_temperature_gpu]
                                       )
        setting_temperature_cpu.change(fn=update_temperature_label,
                                       inputs=[setting_temperature_cpu]
                                       )

        setting_send_button.click(self.button_setting,
                                  inputs=all_args,
                                  outputs=[setting_history])
        im_line_notify_send_button.click(self.button_line,
                                         inputs=all_args,
                                         outputs=[im_line_notify_history])
        im_telegram_send_button.click(self.button_telegram,
                                      inputs=all_args,
                                      outputs=[im_telegram_notify_history])
        im_discord_send_button.click(self.button_discord,
                                     inputs=all_args,
                                     outputs=[im_discord_notify_history])
        setting_timer_start.click(self.timer,
                                  inputs=all_args,
                                  outputs=[setting_history])
        setting_timer_cancel.click(self.timer_cancel)
        im_line_notify_token.change(fn=None,
                                    _js="function(v){localStorage.setItem('im_line_notify_token',v)}",
                                    inputs=im_line_notify_token)
        im_telegram_token_botid.change(fn=None,
                                       _js="function(v){localStorage.setItem('im_telegram_token_botid',v)}",
                                       inputs=im_telegram_token_botid)
        im_telegram_token_chatid.change(fn=None,
                                        _js="function(v){localStorage.setItem('im_telegram_token_chatid',v)}",
                                        inputs=im_telegram_token_chatid)

        #hot fix stable-diffusion-webui-forge
        # gr_blocks.load(fn=None, outputs=[im_line_notify_token, im_telegram_token_botid, im_telegram_token_chatid],
        #                _js="function(){return ["
        #                    "localStorage.getItem('im_line_notify_token'),"
        #                    "localStorage.getItem('im_telegram_token_botid'),"
        #                    "localStorage.getItem('im_telegram_token_chatid')]}")

        # gr_blocks.load(fn=None, inputs=None, outputs=[im_telegram_token_botid], _js="function(){load_LocalStorge('auto-msg-realtime-line-notify-token', 'auto-msg-realtime-line-notify-token')}")
        # gr_blocks.load(fn=None, inputs=None, outputs=[im_telegram_token_chatid], _js="function(){load_LocalStorge('auto-msg-realtime-telegram-bot-chat-id', 'auto-msg-realtime-telegram-bot-chat-id')}")

        return all_args

    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") == "txt2img_prompt":
            self.boxx = component
        if kwargs.get("elem_id") == "img2img_prompt":
            self.boxxIMG = component
        # if kwargs.get("elem_id") == "auto-msg-realtime-line-notify-token":
        #     im_line_notify_token

    def postprocess(self, p, processed, *args):
        # log.warning(f"[9][postprocess][ p, processed, *args]: {print_obj_x(p)} {print_obj_x(processed)} {args}")
        # for arg in args:
        #     print_obj_x(arg)
        # args_keys = objs_2_names(args)
        global args_dict
        args_dict = dict(zip(args_keys, args))
        if (args_dict.get('setting__im_line_notify_enabled') or
                args_dict.get('setting__im_telegram_enabled') or
                args_dict.get('setting__im_discord_enabled')):
            if EnumTriggetType.SDIMAGE.value in args_dict.get('setting_trigger_type'):
                self.send_msg_all_from_processing(p, *args)


def trim_string(s: str, limit: int, ellipsis='…') -> str:
    s = s.strip()
    if len(s) > limit:
        return s[:limit - 1].strip() + ellipsis
    return s


def getname(obj):
    try:
        name = obj.__name__
    except AttributeError as e:
        name = re.match("^'(.*)'", str(e)).group(1)
    return name


def objs_2_names(objs):
    r = []
    for o in objs:
        r.append(getname(o))
    log.warning(f"[][]objs_2_names]: {r}")
    return r


def print_obj_x(obj):
    for attr in dir(obj):
        if not attr.startswith("__"):
            print(attr + "==>", getattr(obj, attr))


args_keys = ['setting__im_line_notify_enabled', 'setting__im_telegram_enabled',
             'setting_trigger_type', 'setting_image_count', 'setting_time_count',
             'setting_temperature_gpu', 'setting_temperature_cpu', 'setting_send_content_with',
             'im_line_notify_token', 'im_line_notify_msg_header',
             'im_telegram_token_botid', 'im_telegram_token_chatid', 'im_telegram_msg_header',
             'setup_enum_send_image_result_radio',
             'setting__im_discord_enabled', 'im_discord_token_botid',
             'im_discord_token_chatid', 'im_discord_msg_header']
on_image_saved_params = []
args_dict = None


def on_image_saved(params):
    global on_image_saved_params
    on_image_saved_params.append(params)
    # log.warning(f"[event][on_image_saved][params]: {on_image_saved_params} {print_obj_x(on_image_saved_params)} {params} {print_obj_x(params)}")


# filename==> output\txt2img-images\fantasticmix_k2\13898-3902715526.png
# image==> <PIL.Image.Image image mode=RGB size=768x1024 at 0x2D7C4A3D900>
# p==> <modules.processing.StableDiffusionProcessingTxt2Img object at 0x000002D691072F20>
# pnginfo==> {'parameters': '1girl,nsfw,bare shoulders,, <lora:ip-adapter-faceid-plusv2_sd15_lora:1>, <lora:LCM_15:1>\nNegative prompt: low quality,badhandv4,bad-picture-chill-75v,\nSteps: 6, Sampler: Euler a, Schedule type: Automatic, CFG scale: 1.5, Seed: 3902715526, Size: 768x1024, Model hash: 19bbe9faa4, Model: fantasticmix_k2, Clip skip: 2, Lora hashes: "ip-adapter-faceid-plusv2_sd15_lora: a95a0f4bdcb9, LCM_15: aaebf6360f7d", TI hashes: "badhandv4: 5e40d722fc3d, bad-picture-chill-75v: 7d9cc5f549d7", Downcast alphas_cumprod: True, Version: v1.10.1'}

# def postprocess_image(self, p, pp, *args):
#     log.warning(f"[1][postprocess_image][ p, processed, *args]: {print_obj_x(p)} {print_obj_x(pp)} {args}")
#
# def postprocess_image_after_composite(self, p, pp, *args):
#     log.warning(
#         f"[2][postprocess_image_after_composite][ p, processed, *args]: {print_obj_x(p)} {print_obj_x(pp)} {args}")
#
# def process(self, p, *args):
# log.warning(f"[0][process][p, *args]: {print_obj_x(p)} {args}")

# indication = enum.Enum('Indication', dict(keys))
# def init_value():
#     const elems = document.getElementsByTagName('gradio-app');
#     container = gradioApp().getElementById('script_txt2img_adetailer_ad_main_accordion');

script_callbacks.on_image_saved(on_image_saved)
# script_callbacks.on_app_started(init_value )
# https://builtin.com/software-engineering-perspectives/convert-list-to-dictionary-python
