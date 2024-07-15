import time
import streamlit as st
import re
import subprocess
import ffmpeg
import json

file_name =  'livechat.live_chat.json'
output_file_name = "chat.txt"
cookie = ''

def run_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return stdout.decode("utf-8"), stderr.decode("utf-8"), process.returncode

def remove_timestamp_from_youtube_url(url):
    # 正規表現パターンでタイムスタンプを検索して除去する
    pattern = r'(&|\?)t=\d+s?'
    clean_url = re.sub(pattern, '', url)
    return clean_url

def save_messages_to_file(filename_in, filename_out):
    try:
        with open(filename_in, 'r', encoding='utf-8') as f_in, open(filename_out, 'w', encoding='utf-8') as f_out:
            lines = f_in.readlines()

            for line in lines:
                try:
                    data = json.loads(line.strip())
                    if 'liveChatTextMessageRenderer' in data.get('replayChatItemAction', {}).get('actions', [{}])[0].get('addChatItemAction', {}).get('item', {}):
                        message = data['replayChatItemAction']['actions'][0]['addChatItemAction']['item']['liveChatTextMessageRenderer']['message']['runs'][0]['text']
                        timestamp = data['replayChatItemAction']['actions'][0]['addChatItemAction']['item']['liveChatTextMessageRenderer']['timestampText']['simpleText']
                        f_out.write(f"{timestamp}\t{message}\n")
                        #print(f"{timestamp}\t{message}")
                    else:
                        # f_out.write("No message found.\n")
                        pass
                except json.JSONDecodeError as e:
                    print(f"JSONDecodeError on line: {line.strip()}")
                    print(f"Error: {e.msg} at line {e.lineno}, column {e.colno}")
                except Exception as e:
                    # print(f"Unexpected error: {e}")
                    pass

    except Exception as e:
        print(f"Error: {e}")

def convert_timestamp_to_seconds(timestamp):
    parts = timestamp.split(':')
    if len(parts) == 2:
        hours, minutes = 0, int(parts[0])
        seconds = int(parts[1])
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
    else:
        raise ValueError("Invalid timestamp format")

    total_seconds = hours * 3600 + minutes * 60 + seconds - 15
    return total_seconds

def search_strings_in_file(file_path, search_strings, search_mode='OR', youtube_url=''):
    out = ''
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        if search_mode.upper() == 'OR':
            matching_lines = [line.strip() for line in lines if any(search_string in line for search_string in search_strings)]
        elif search_mode.upper() == 'AND':
            matching_lines = [line.strip() for line in lines if all(search_string in line for search_string in search_strings)]
        else:
            matching_lines = [line.strip() for line in lines]

        if matching_lines:
            #print(f"Lines containing {search_mode} of {search_strings}:")
            for line in matching_lines:
                parts = line.split('\t')
                timestamp = parts[0]
                content = '\t'.join(parts[1:])

                # Convert timestamp to seconds
                seconds = convert_timestamp_to_seconds(timestamp)

                # Generate YouTube URL
                youtube_link = f"{youtube_url}&t={seconds}"

                # Print line with YouTube URL
                out +=  f"{timestamp} {content} {youtube_link}" 
                text_with_link = f"[{timestamp}]({youtube_link}):{content}"

                st.markdown(text_with_link)
                #st.write(f"{timestamp} {content} {youtube_link}" )
                print(f"{timestamp} {content} {youtube_link}")
        else:
            print(f"No lines containing {search_mode} of {search_strings} found.")

    except FileNotFoundError:
        print(f"The file at {file_path} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
        
    return out

def main():
    st.title('YouTube Live コメント検索')

    st.header('Step1')
    youtube_url = st.text_input("URLを入力してください",placeholder="https://www.youtube.com/watch?v=JLwnwVm74Ak")
    youtube_url = remove_timestamp_from_youtube_url(youtube_url)
    st.write(youtube_url)


    membership = st.checkbox('メンバーシップ限定放送')

        
    
    if membership:
        st.markdown(
            """
            <div style='border: 1px solid #ccc; padding: 10px;'>
                YouTubeのメンバーシップ限定の動画をダウンロードするためには、
                yt-dlpに適切な認証情報（クッキー）を渡す必要があります。<br>
                ブラウザからエクスポートしたクッキーを使って、yt-dlpがメンバーシップの動画にアクセスできるようにします。<br>
                具体的には以下の動画を参照ください。
            </div>
            """,
            unsafe_allow_html=True
        )

        
        uploaded_file = st.file_uploader("cookies.txt", type=['txt'])

        # ファイルがアップロードされた場合の処理
        if uploaded_file is not None:
            # ファイルの内容を文字列として読み込む
            cookie = uploaded_file.read().decode('utf-8')
            with open('cookie.txt', 'w') as file:
                file.write(cookie)



    st.header('Step2')
    command = 'yt-dlp --cookies ./cookie.txt --write-sub --sub-lang live_chat --skip-download '+ youtube_url +' -o livechat'

    if st.button("チャット抽出"):
        if command:
            stdout, stderr, returncode = run_command(command)
            if returncode == 0:
                st.success("コマンドが正常に実行されました。")
                st.code(stdout)
            else:
                st.error("コマンドの実行中にエラーが発生しました。")
                st.code(stderr)
                
        save_messages_to_file(file_name, output_file_name)

    st.header('Step3')

    option = st.radio(
        "検索モード",
        ("AND", "OR", "全検索")
    )
    
    
    search_strings = []
    if not(option == "全検索"):
        search_word = st.text_input("検索ワードを入力してください",placeholder="ワード1  ワード2")
        search_strings = search_word.split()

    search_mode = option  # 'OR' または 'AND' を指定
    if st.button('検索'):
        out = search_strings_in_file(output_file_name, search_strings, search_mode, youtube_url)




        
    
    
if __name__ == '__main__':
    main()