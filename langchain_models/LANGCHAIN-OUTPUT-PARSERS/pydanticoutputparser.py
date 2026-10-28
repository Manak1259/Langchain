from langchain_openai import ChatOpenAI

from dotenv import load_dotenv

from langchain_core.prompts import PromptTemplate

from langchain_core.output_parsers import PydanticOutputParser

from pydantic import BaseModel, Field

load_dotenv(dotenv_path='.env')


# Use the existing OpenAI key from .env so the model follows the JSON schema reliably.
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

class Person(BaseModel):

    name: str = Field(description= "Name of the person")
    age: int = Field(description= "age of the person")
    city: str = Field(description= "name of the city the person belongs to")


parser = PydanticOutputParser(pydantic_object=Person)

template = PromptTemplate(
    template=(
        "Generate a fictional person in {place}. "
        "Return ONLY valid JSON matching the schema below, with no markdown, no code fences, and no explanation. "
        "{format_instructions}"
    ),
    input_variables=['place'],
    partial_variables={'format_instructions': parser.get_format_instructions()}
)

# prompt = template.invoke({'place': 'india'})

# result = model.invoke(prompt)

# final_result = parser.parse(result.content)

# print(final_result)

chain = template | model | parser

final_result = chain.invoke({'place': 'india'})

print(final_result)