import datetime
import enum
import logging
import os
from threading import Timer

import gradio as gr
import pyautogui
import requests

from modules import scripts, script_callbacks
from modules.processing import StableDiffusionProcessingTxt2Img

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


class EnumSendContent(enum.Enum):
    SDIMAGE = 'SD-Image-generated'
    ScreenShot = 'ScreenShot'
    TextPrompt = 'Text-Prompt'
    Text_neg_prompt = 'Text-neg_prompt'
    Text_Temperature = 'Text-Temperature'

    @classmethod
    def values(cls):
        return [e.value for e in cls]


class EnumTriggetType(enum.Enum):
    SDIMAGE = 'SD-Image-generated'
    TIMER = 'Timer Countdown'
    STATE_TEMPERATURE_GPU = 'STATE-Temperature-GPU'
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





class AutoMessaging(scripts.Script):

    def __init__(self) -> None:
        super().__init__()

    def title(self):
        return ("Link fetcher")

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    lin_notify_history_array = []
    telegram_bot_history_array = []
    timer_couunt_threading = None

    # bot_line_notify_trigger_by_temperature_label = "60°C/140°F"
    # def on_image_saved_x(self, params):  # image, p, filename, pnginfo
    #     log.warning(f"[][script_callbacks][on_image_saved_x] name:{params.filename} {params.pnginfo}")
    #     self.on_image_saved_params = params

    def send_msg_all_from_processing(self, p, setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                     setting_trigger_type, setting_image_count, setting_time_count,
                                     setting_temperature,
                                     setting_send_content_with,
                                     im_line_notify_token, im_line_notify_msg_header,
                                     im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header):

        if EnumSendContent.TextPrompt.value in setting_send_content_with:
            im_line_notify_msg_header += p.prompt
            im_telegram_msg_header += p.prompt

        if EnumSendContent.Text_neg_prompt.value in setting_send_content_with:
            im_line_notify_msg_header += p.prompt
            im_telegram_msg_header += p.prompt

        self.send_msg_all_lets_go(setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                  setting_trigger_type, setting_image_count, setting_time_count, setting_temperature,
                                  setting_send_content_with,
                                  im_line_notify_token, im_line_notify_msg_header,
                                  im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header)

    def send_msg_all_lets_go(self, setting__im_line_notify_enabled, setting__im_telegram_enabled,
                             setting_trigger_type, setting_image_count, setting_time_count, setting_temperature,
                             setting_send_content_with,
                             im_line_notify_token, im_line_notify_msg_header,
                             im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header):

        opened_files = []
        base_folder = os.path.dirname(__file__)
        global on_image_saved_params
        if on_image_saved_params is not None:
            im_line_notify_msg_header += str(on_image_saved_params.pnginfo)
            im_telegram_msg_header += str(on_image_saved_params.pnginfo)
            image_path = os.path.join(base_folder, "..", "..", "..",  on_image_saved_params.filename)
            log.warning(f"[][send_msg_all_lets_go][self.on_image_saved_params is not None] image_path:{image_path}")
            image = open(image_path, 'rb')
            opened_files.append(image)
            on_image_saved_params = None

        if EnumSendContent.ScreenShot.value in setting_send_content_with:
            myscreenshot = pyautogui.screenshot()
            image_path = os.path.join(base_folder, "..", "myScreenshot.png")
            myscreenshot.save(image_path)
            image = open(image_path, 'rb')
            opened_files.append(image)

        result_line_notify = None
        result_telegram_bot = None

        if setting__im_line_notify_enabled:
            result_line_notify = self.send_msg_linenotify(opened_files, im_line_notify_token, im_line_notify_msg_header)
            log.warning(f"[][send_msg_all][result_line_notify]: {result_line_notify}")

        if setting__im_telegram_enabled:
            result_telegram_bot = self.send_msg_telegram(opened_files, im_telegram_token_botid,
                                                         im_telegram_token_chatid,
                                                         im_telegram_msg_header)
            log.warning(f"[][send_msg_all][result_telegram_bot]: {result_telegram_bot}")

        if EnumTriggetType.TIMER.value in setting_trigger_type:
            self.timer_couunt_threading = Timer(setting_time_count, self.send_msg_all_lets_go,
                                                [setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                                 setting_trigger_type, setting_image_count, setting_time_count,
                                                 setting_temperature, setting_send_content_with,
                                                 im_line_notify_token, im_line_notify_msg_header,
                                                 im_telegram_token_botid, im_telegram_token_chatid,
                                                 im_telegram_msg_header])
            self.timer_couunt_threading.start()
            log.warning(f"[][send_msg_all][Timer] Countdown in: {setting_time_count} secs")

        else:
            if self.timer_couunt_threading is not None:
                self.timer_couunt_threading.cancel()
                self.timer_couunt_threading = None
                log.warning(f"[][send_msg_all][Timer] Canceled.")

        if opened_files.__len__() > 0:
            for img in opened_files:
                img.close()
        return [self.lin_notify_history_array[0], self.telegram_bot_history_array[0]]

    def send_msg_linenotify(self, opened_files, im_line_notify_token, im_line_notify_msg_header):
        # msg_all = msg_all + str(bot_line_notify_trigger_by) + str(bot_line_notify_send_with)
        url = 'https://notify-api.line.me/api/notify'
        headers = {
            'Authorization': 'Bearer ' + im_line_notify_token
        }
        data = {
            'message': im_line_notify_msg_header
        }

        if opened_files.__len__() > 0:
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
        log.warning(
            f"[][][send_msg_telegram]: {opened_files, im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header}")

        assert type(im_telegram_msg_header) == str, "must be str"
        # msg_all = bot_telegram_msg_header + str(bot_line_notify_trigger_by) + str(bot_line_notify_send_with)
        headers = {'Content-Type': 'application/json', "cache-control": "no-cache"}

        # API ref: https://core.telegram.org/bots/api#sendphoto
        if opened_files.__len__() > 0:
            url = f'https://api.telegram.org/bot{im_telegram_token_botid}/sendPhoto'
            data = {"chat_id": im_telegram_token_chatid, "caption": im_telegram_msg_header}
            for img in opened_files:
                img.seek(0)
                imagefile = {'photo': img}
                # result = requests.post(url, headers=headers, data=json.dumps(data), files=imagefile)
                result = requests.post(url, params=data, files=imagefile)
                log.warning(f"[][][send_msg_telegram]w/image: {result}")

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

    def tel_getupdate(self, im_telegram_token_botid):
        url = f'https://api.telegram.org/bot{im_telegram_token_botid}/getUpdates'
        result = requests.post(url)
        return result.text

    def update_temperature_label(self, celsius):
        fahrenheit = round((celsius * 1.8) + 32, 1)
        result = f" {celsius}°C/{fahrenheit}°F"
        log.warning(f"[][][update_temperature_label]result: {result}")
        # self.bot_line_notify_trigger_by_temperature.info = result
        return result

    def ui(self, is_img2img):
        with gr.Blocks():
            # gr.Markdown("Blocks")
            with gr.Accordion(open=False, label="Auto Messaging Realtime v20240808"):
                with gr.Tab("MSG Info"):
                    gr.Markdown(
                        "* IF [XXX] then [YYY] \n"
                        "* 1 XXX= image (send by each/every 1-100 image generated) \n"
                        "* 2 XXX= time (send by every seconds. (0 to disable))\n"
                        "* 3 XXX= PC-state (GPU)\n"
                        "* 4 YYY= send text \n"
                        "* 5 YYY= send image \n"
                    )
                    setting__im_line_notify_enabled = gr.Checkbox(label="0. Enable LINE-Notify", value=False)
                    setting__im_telegram_enabled = gr.Checkbox(label="0.Enable Telegram-bot", value=False)

                    setting_trigger_type = gr.CheckboxGroup(
                        EnumTriggetType.values(),
                        value=EnumTriggetType.values(),
                        label="1.  IF [[[ XXX ]]] Then YYY",
                        info="When should send? trigger events by XXX?")
                    with gr.Row():
                        setting_image_count = gr.Slider(1, 100, value=1,
                                                        label="2.1 " + EnumTriggetType.SDIMAGE.value + " count",
                                                        step=1,
                                                        info="[" + EnumTriggetType.SDIMAGE.value + "] send msg by generate count")
                        setting_time_count = gr.Slider(0, 6000, value=60,
                                                       label="2.2  " + EnumTriggetType.TIMER.value,
                                                       step=1,
                                                       info="[" + EnumTriggetType.TIMER.value + "]send by seconds. ")
                    with gr.Row():
                        setting_temperature_gpu = gr.Slider(0, 100, value=60,
                                                            label="2.3 " + EnumTriggetType.STATE_TEMPERATURE_GPU.value + " limit °C",
                                                            step=1,
                                                            info="[" + EnumTriggetType.STATE_TEMPERATURE_GPU.value + "] 60°C/140°F")
                        setting_temperature_cpu = gr.Slider(0, 100, value=60,
                                                            label="2.4 " + EnumTriggetType.STATE_TEMPERATURE_CPU.value + " limit °C",
                                                            step=1,
                                                            info="[" + EnumTriggetType.STATE_TEMPERATURE_CPU.value + "] 60°C/140°F")

                    setting_send_content_with = gr.CheckboxGroup(
                        EnumSendContent.values(),
                        value=EnumSendContent.values(),
                        label="3. IF XXX Then [[[ YYY ]]]",
                        info="Send what? then YYY(send text, image or both)?")
                    setting_history = gr.Dataframe(
                        interactive=True,
                        wrap=True,
                        label="4. History",
                        headers=["TimeStamp", "Response", "Msg"],
                        datatype=["str", "str", "str"],
                        row_count=3,
                        col_count=(3, "fixed"),
                    )
                    setting_send_button = gr.Button(
                        "Test Send All (trigger ALL IMs enabled)")

                with gr.Tab("LINE-Notify"):
                    gr.Markdown("* LINE-Notify only need [Token]\n"
                                "* add Notify as friend or add that to group, which don`t need chatID")

                    im_line_notify_token = gr.Textbox(label="1.[im_line_notify_token]", lines=1,
                                                      value="tcnDSnAR6Gl6pTMBfQ4wOxqtq0eSyXqqJ9Q1Hck4dRO",
                                                      placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                                                      )
                    im_line_notify_msg_header = gr.Textbox(label="2. [msg header]", lines=1,
                                                           value="[send from web-ui-line-notify]",
                                                           placeholder="[send from web-ui]"
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
                                                             value="7376923093:AAGtCtd9Ogiq9yT1IBsbRD6ENQ5DbAqL6Ig",
                                                             placeholder="7376923093:AAGtCtd9Ogiq9yT1IBsbRD6ENQ5DbAqL6Ig"
                                                             )
                        im_telegram_getupdates_result = gr.JSON()
                    im_telegram_getupdates = gr.Button("1.2 Get Token Info: ChatId")

                    with gr.Row():
                        im_telegram_token_chatid = gr.Textbox(label="2.1 [ChatID] ", lines=1,
                                                              info="format:1234567890. can be send to personal or group",
                                                              value="1967680189",
                                                              placeholder="1967680189"
                                                              )

                        im_telegram_msg_header = gr.Textbox(label="2.2 [msg header]", lines=1,
                                                            info="append on every message. like prompt or temperature.",
                                                            value="[send from web-ui-telegram-bot]",
                                                            placeholder="[send from web-ui]"
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
                with gr.Tab("WhatsApp&others"):
                    gr.Markdown(
                        "* Seems only for business use, I can`t find the way now. IF u know or others IM app, plz let me know. leave command on git. https://github.com/xlinx/sd-webui-decadetw-auto-messaging-realtime")

        im_telegram_getupdates.click(self.tel_getupdate,
                                     inputs=[im_telegram_token_botid],
                                     outputs=[im_telegram_getupdates_result])
        setting_temperature_gpu.change(fn=self.update_temperature_label,
                                       inputs=setting_temperature_gpu
                                       )
        setting_send_button.click(self.send_msg_all_lets_go,
                                  inputs=[setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                          setting_trigger_type, setting_image_count, setting_time_count,
                                          setting_temperature_gpu, setting_send_content_with,
                                          im_line_notify_token, im_line_notify_msg_header,
                                          im_telegram_token_botid, im_telegram_token_chatid, im_telegram_msg_header],
                                  outputs=[setting_history])
        im_line_notify_send_button.click(self.send_msg_all_lets_go,
                                         inputs=[setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                                 setting_trigger_type, setting_image_count, setting_time_count,
                                                 setting_temperature_gpu, setting_send_content_with,
                                                 im_line_notify_token, im_line_notify_msg_header,
                                                 im_telegram_token_botid, im_telegram_token_chatid,
                                                 im_telegram_msg_header],
                                         outputs=[im_line_notify_history])
        im_telegram_send_button.click(self.send_msg_all_lets_go,
                                      inputs=[setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                              setting_trigger_type, setting_image_count, setting_time_count,
                                              setting_temperature_gpu, setting_send_content_with,
                                              im_line_notify_token, im_line_notify_msg_header,
                                              im_telegram_token_botid, im_telegram_token_chatid,
                                              im_telegram_msg_header],
                                      outputs=[im_telegram_notify_history])
        return [setting__im_line_notify_enabled, setting__im_telegram_enabled,
                setting_trigger_type, setting_image_count, setting_time_count,
                setting_temperature_gpu, setting_send_content_with,
                im_line_notify_token, im_line_notify_msg_header,
                im_telegram_token_botid, im_telegram_token_chatid,
                im_telegram_msg_header]

    def after_component(self, component, **kwargs):
        if kwargs.get("elem_id") == "txt2img_prompt":
            self.boxx = component
        if kwargs.get("elem_id") == "img2img_prompt":
            self.boxxIMG = component

    def process(self, p: StableDiffusionProcessingTxt2Img,
                setting__im_line_notify_enabled, setting__im_telegram_enabled,
                setting_trigger_type, setting_image_count, setting_time_count,
                setting_temperature, setting_send_content_with,
                im_line_notify_token, im_line_notify_msg_header,
                im_telegram_token_botid, im_telegram_token_chatid,
                im_telegram_msg_header):
        log.warning(f"[1][process][setting_trigger_type]: {setting_trigger_type} ")

        if setting__im_line_notify_enabled or setting__im_telegram_enabled:
            self.send_msg_all_from_processing(p, setting__im_line_notify_enabled, setting__im_telegram_enabled,
                                              setting_trigger_type, setting_image_count, setting_time_count,
                                              setting_temperature,
                                              setting_send_content_with,
                                              im_line_notify_token, im_line_notify_msg_header,
                                              im_telegram_token_botid, im_telegram_token_chatid,
                                              im_telegram_msg_header)


# def on_after_component(component, **_kwargs):
#     global txt2img_submit_button, img2img_submit_button
#     if getattr(component, "elem_id", None) == "txt2img_generate":
#         txt2img_submit_button = component
#         return
#     if getattr(component, "elem_id", None) == "img2img_generate":
#         img2img_submit_button = component

#name:output\txt2img-images\fantasticmix_k2\10595-3748719078.png
# {
# 'parameters': '1girl,A superstar on stage.,, <lora:LCM_15:1>, <lora:ip-adapter-faceid-plusv2_sd15_lora:1>\nNegative
# prompt: MajicNegative_V2,badhandv4,\nSteps: 6, Sampler: LCM, Schedule type: Automatic, CFG scale: 1.5, Seed: 3748719078,
# Size: 768x1024, Model hash: 19bbe9faa4, Model: fantasticmix_k2, VAE hash: 07af11b95c, VAE: vae-ft-mse-840000-ema-pruned.safetensors,
# Clip skip: 2, Lora hashes: "LCM_15: aaebf6360f7d, ip-adapter-faceid-plusv2_sd15_lora: a95a0f4bdcb9",
# TI hashes: "MajicNegative_V2: a53884ef726b, badhandv4: 5e40d722fc3d", Downcast alphas_cumprod: True, Version: v1.9.4'}

on_image_saved_params = None
def on_image_saved(params):  #image, p, filename, pnginfo
    global on_image_saved_params
    on_image_saved_params = params


# script_callbacks.on_ui_settings(on_ui_settings)
# script_callbacks.on_after_component(on_after_component)
# script_callbacks.on_app_started(add_api_endpoints)
# script_callbacks.on_before_ui(on_before_ui)
script_callbacks.on_image_saved(on_image_saved)
