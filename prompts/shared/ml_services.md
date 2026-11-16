version=4
# 3rd Party ML Services and Technologies Analysis

You are a machine learning and AI systems analyst. Analyze this codebase to identify and document all 3rd party machine learning services, AI technologies, and ML-related integrations.

**Special Instruction**: Focus ONLY on identifying services, tools, and mechanisms that are ACTUALLY USED in this codebase. Do NOT list ML services, frameworks, or tools that are not present in the code.

## Analysis Requirements

### 1. **External ML Service Providers**
Identify any usage of:
- **Cloud ML Services**: AWS SageMaker, Azure ML, Google AI Platform, Databricks, etc.
- **AI APIs**: OpenAI, Anthropic, Groq, Cohere, Hugging Face Inference API, etc.
- **Specialized Services**: Speech recognition (AWS Transcribe, Google Speech-to-Text), computer vision (AWS Rekognition, Google Vision), etc.
- **MLOps Platforms**: MLflow, Weights & Biases, Neptune, ClearML, etc.

### 2. **ML Libraries and Frameworks**
Document usage of:
- **Deep Learning**: PyTorch, TensorFlow, JAX, Keras, etc.
- **Traditional ML**: Scikit-learn, XGBoost, LightGBM, CatBoost, etc.
- **NLP**: Transformers, spaCy, NLTK, Gensim, etc.
- **Computer Vision**: OpenCV, PIL/Pillow, torchvision, etc.
- **Audio/Speech**: Whisper, librosa, speechbrain, etc.

**Note**: When looking for dependencies, package names, or library names, perform case-insensitive matching and consider variations with dashes between words (e.g., "tensor-flow", "scikit-learn", "hugging-face").

### 3. **Pre-trained Models and Model Hubs**
Look for:
- **Hugging Face Models**: Model downloads, transformers usage
- **Other Model Sources**: TensorFlow Hub, PyTorch Hub, custom model repositories
- **Specific Models**: BERT, GPT variants, Whisper, CLIP, etc.

### 4. **AI Infrastructure and Deployment**
Analyze:
- **Model Serving**: TorchServe, TensorFlow Serving, MLflow, custom solutions
- **Containerization**: Docker images with ML dependencies
- **GPU/Hardware**: CUDA usage, TPU integration, specialized hardware requirements
- **Scaling**: Auto-scaling for ML workloads, batch processing systems

## Analysis Format

For each identified ML technology, provide:

### AI Service/Technology Name
- **Type**: [External API / Self-hosted Library / Pre-trained Model / Infrastructure]
- **Purpose**: Brief description of what it's used for
- **Integration Points**: Where in the codebase it's used
- **Configuration**: How it's configured (environment variables, config files)
- **Dependencies**: Required packages, versions, hardware requirements
- **Cost Implications**: If applicable, pricing model or resource requirements
- **Data Flow**: What data is sent to external services (if any)
- **Criticality**: How essential it is to the application's functionality

## Security and Compliance Considerations

Document:
- **API Keys/Credentials**: How ML service credentials are managed
- **Data Privacy**: What data is sent to 3rd party ML services
- **Model Security**: How models are secured and validated
- **Compliance**: Any regulatory requirements (GDPR, HIPAA, etc.) affecting ML usage

## Code Examples

Include relevant code snippets that demonstrate:
- Service integration patterns
- Configuration examples
- Error handling for ML services
- Model loading and inference patterns

## Current Implementation Analysis

Document the current state of:
- **Cost Patterns**: ML service costs based on current usage
- **Performance Characteristics**: Current performance implementation
- **Security Implementation**: Security measures currently in place for ML integrations
- **Reliability Patterns**: Current fault tolerance and backup implementations
- **Vendor Dependencies**: Current dependencies on specific ML providers

## Summary

Conclude with:
- **Total Count**: Number of 3rd party ML services identified
- **Major Dependencies**: Most critical ML dependencies
- **Architecture Pattern**: Overall ML architecture approach (API-first, self-hosted, hybrid)
- **Risk Assessment:** Key risks and dependencies on external ML services

{previous_context}

---

## Dependencies

{repo_deps}
