# sd-webui-decadetw-Auto-Messaging-realtime
* Automatic1111 extension
* Messaging by time | result | states
  * every 10|60|120 sec
  * each result image generated
  * temperature state too high
* Messaging to you or group
  * image result, 
  * prompt, 
  * web-ui setting, 
  * PC state (like: CPU, GPU temperature)
    * https://github.com/w-e-w/stable-diffusion-webui-GPU-temperature-protection


## Motivation

* When u outdoor
* Just look IM app to check result from web-ui
* [Rx] Monitor ur Web-ui when u eating, GYM, working
  * image, info-text, info-temperature
* [Tx] Control ur Web-ui when u eating, GYM, working (not yet)
  * type message as command to stop gen-forever

<img width="30%" src="https://scdn.line-apps.com/n/line_notice/img/pc/img_lp02_zh_TW.png?20161005">
<img width="10%" src="https://core.telegram.org/file/811140934/1/tbDSLHSaijc/fdcc7b6d5fb3354adf">

---


## Installtion

* You need get Messaging access token first. 
  * LINE Notify (basic usage, receive from web-ui)
    * You need get Token, 
    * then add LINENotify to where u want recive place(can be a group or just u)
    * 1. https://notify-bot.line.me/
    * 2. free for 1000 request /per token
    * 3. ever account can have 100 tokens max 
    * 4. limit info https://notify-bot.line.me/doc/en/
  * LINE bot messaging-api (in advance, u can send message control web-ui)
    * https://developers.line.biz/zh-hant/services/messaging-api/
  * Telegram 
    * You need get BotToken & ChatId
      * https://core.telegram.org/bots#6-botfather
      * https://t.me/botfather
    * get BotToken
      * add botfather inside ur telgram
      * type "/newbot"
      * type "XXXXXXXX_bot"
      * then, u will get botToken
      * then add this bot as ur friend
    * get ChatId
      * replace YOUR_BOT_TOKEN
        * https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
  * WhatsApp
    * seems only for business
    * https://business.whatsapp.com/products/business-platform
  * IFTTT (share what's funny how u interactive with web-ui)
    * https://ifttt.com/line
    * https://ifttt.com/explore

  


## Colophon

Made for fun. I hope if brings you great joy, and perfect hair forever. Contact me with questions and comments, but not threats, please. And feel free to contribute! Pull requests and ideas in Discussions or Issues will be taken quite seriously!
--- https://decade.tw

