"""
Prompts should help the user define advanced concepts which follow leading edge
best practices for performance and accuracy while being incredibly easy to use. 

## Inspiration
DSPy incorporates a syntax for prompting and also allows verifying and tuning the 
performance of those prompts. 

They also have defined input and output types via their own syntax. (Is this something
that a Pydantic Model would be better suited for?)

## Progression
DSPy uses a proprietary syntax for metadata which will be parsed after the completion 
is returned, so it's possible that we can gain more performance by using XML 
(recommended first hand by Anthropic) or JSON. 

The syntax for tool calls is often handled by te framework, but maybe we can patch in 
and override to make it more performant. 

OpenAI will return structured output based on a Pydantic Model, so that may be
a way to gain accuracy in response data, and incorporate metadata like `thinking`. 
Other providers do not support this, so there would need to be a fallback. 

We don't want to write this from scratch, but if there are enough tradeoffs 
involved in using existing solutions, it's an option.

## Use by Frameworks
At the end of the day, a prompt is just a string, so let's keep that in mind. 

It would be nice to just use DSPy's backend for testing and improvement, but we 
still need to be able to pass the generated prompts to the framework of our choosing. 
 - Do all frameworks give us a way to modify the system prompts and inject our own?
 - How do we handle model selection for training runs?
 - Internally DSPy is pretty rough, and is probably evolving rapidly. Avoid using
    too much of the low level library as it will likely change. 
 - DSPy terminology for internal concepts is not intuitive so let's shelter our
    user from too much of it. 

As it stands, we have two types of interactions with the agent stack: Agents and Tasks.
```
Agent
    role: 
    goal: 
    backstory: 

Task
    description:
    expected_output: 
```

We use CrewAI's templates (outside of crew projects) to concatenate those fields, 
which are very basic. 

### CrewAI
`crew.Agent:`
    https://github.com/crewAIInc/crewAI/blob/main/src/crewai/agent.py#L41
    `use_system_prompt` (bool) allows us to disable the system prompt
    `system_template` (str) TODO documented as "System format for the agent."
    `prompt_template` (str) TODO documented as "Prompt format for the agent."
    `response_template` (str) TODO documented as "Response format for the agent."

`crew.Task:`
    https://github.com/crewAIInc/crewAI/blob/main/src/crewai/task.py#L47
    `output_json` (bool?) TODO
    `output_pydantic` (bool?) TODO

`crewai.utilities.prompts.Prompts`
    https://github.com/crewAIInc/crewAI/blob/main/src/crewai/utilities/prompts.py#L8
    Builds a prompt using and Agent definition, and also handles tools. This is where
    the booleans from `crew.Agent` are interpreted. 

Other notable functions:

`Agent.i18n.slice(<str>)` crew uses i18n internally to allow for prompts to 
    be translated in the future; possible we can overload another language and 
    inject new prompt templates. This would be earlier than the assembly of the 
    prompt though, so we would only be able to tune the messaging.

`crewai.utilities.converter.generate_model_descriptions` TODO
    https://github.com/crewAIInc/crewAI/blob/main/src/crewai/utilities/converter.py#L230

### LangGraph
LangChain and LangGraph don't include any prompt templates in the frameworks, so 
we are free to implement our own and pass them as messages. 

### OpenAI Swarm
Swarm does not include templated prompts, either, so we're free to pass our own
as strings/messages. 

## Next Steps
- Define the API for interacting with prompts
- Explore hooks that can be used to augment framework prompts
- Supply default system prompt templates that can be modified by the user
- Run evaluations to determine if any of the known tricks help improve performance
    in a quantifiable way. ie. "Think about this step by step" , "Do not hallucinate", 
    "Today is {date}" (performance has been shown to improve on non-holidays for example)
"""

import pydantic


class Prompt(pydantic.BaseModel):
    """Base class for all prompts."""
    pass