from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_core.messages import AIMessage,HumanMessage,SystemMessage
load_dotenv()

model = ChatOpenAI()

# # problem with below code is , it wont have any chat history
# while True:
#     user_input = input('YOU::    ')
#     if user_input == 'exit':
#         break
#     result = model.invoke(user_input)

#     print('AI: ', result.content)

#Code with chathistory
# # not getting the AI and human messgaes properly in human history
# chat_history=[]

# while True:
#     user_input= input('YOU:  ')
#     chat_history.append(user_input)
#     if user_input == 'exit':
#         break
#     result = model.invoke(chat_history)
#     chat_history.append(result.content)
#     print("AI:  ", result.content)

# print(chat_history)
# To resolve the problem with message history
chat_history=[
SystemMessage(content="you are a helpful AI assistent")

]

while True:
    user_input = input('YOU:    ')
    chat_history.append(HumanMessage(content=user_input))
    if user_input == 'exit':
        break
    result = model.invoke(chat_history)
    chat_history.append(AIMessage(content=result.content))
 