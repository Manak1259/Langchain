from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSequence, RunnableParallel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv

load_dotenv()

model =  ChatOpenAI(model="gpt-4o-mini", temperature=0)
parser = StrOutputParser()

prompt1 = PromptTemplate(
    template=' generate a tweet for the given topic {topic}',
    input_variables = ['topic']
)

prompt2 = PromptTemplate(
    template= "generate a linked in post for the given topic {topic}",
    input_variables = ['topic']

)

chain = RunnableParallel({'tweet':RunnableSequence(prompt1, model, parser),
                         'linkedin': RunnableSequence(prompt2, model, parser)})

result = chain.invoke({'topic':"postman"})

print(result)


# Runnable passthrough

joke_gen_chain = RunnableSequence(prompt1, model, parser)

parallel_chain = RunnableParallel({
    'joke': RunnablePassthrough(),
    'explanation': RunnableSequence(prompt2, model, parser)
})

final_chain = RunnableSequence(joke_gen_chain, parallel_chain)

print(final_chain.invoke({'topic':'cricket'}))
