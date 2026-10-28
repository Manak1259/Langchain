from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import TypedDict, Annotated

load_dotenv()

model = ChatOpenAI()
# # normal scehma
# class Review(TypedDict):
   
#     summary: str
#     sentiment: str

#Annotated scema
class Review(TypedDict):
    summary: Annotated[str, "A brief summary of the review"]
    sentiment: Annotated[str,"return sentiments of the review either negative, postive or neutral"]


structure_model = model.with_structured_output(Review) 


result = structure_model.invoke("""the hardware is great, but the software feels bloated. There
are toomany pre-installed apps that I can't remove. Also, the UI looks outdated compared to other
brands. hoping for a softare update to fix this.""")

print(result)

