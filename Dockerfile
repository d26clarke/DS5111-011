# Step 1: Initialize environment using an official light-weight base image
FROM python:3.12-slim

# Step 2: Establish the working environment directory inside the container
WORKDIR /app

# Step 3: Copy only dependency manifests first to maximize layer caching benefits
COPY requirements.txt .

# Step 4: Install runtime python dependencies cleanly without system caching bloating the layer
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy your functional codebase assets down into the image space
COPY bin/ ./bin/
RUN mkdir -p logs/

# Step 6: Define the default interactive streaming entrypoint target command
CMD ["sh", "-c", "python bin/cleanYoutubeIDs.py"]
