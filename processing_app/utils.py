from langchain_text_splitters import RecursiveCharacterTextSplitter

def split_text_into_chunks(text, size, overlap):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=size,
        chunk_overlap=overlap,
        length_function=len,
        is_separator_regex=False,
    )

    chunks = text_splitter.split_text(text)
    return chunks