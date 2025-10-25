from typehints.general import GeneratorClassName


def default_instruction_handler(generator_class_name: GeneratorClassName, instruction):
    print(f"Selected {generator_class_name} instruction: {instruction.name}")
    print(f"Instruction details: {instruction.model_dump()}")
