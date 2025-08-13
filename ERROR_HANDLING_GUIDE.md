# Voice Agent - Error Handling & Robustness Implementation

## Overview

This document outlines the comprehensive error handling and robustness features implemented in the FastAPI Voice Agent application.

## Server-Side Error Handling (run.py)

### 1. Health Check System

-   **Endpoint**: `/health`
-   **Purpose**: Monitor API key availability and system health
-   **Response**:
    -   `healthy` when all API keys are present
    -   `degraded` when one or more API keys are missing
-   **Checks**: MURF_API_KEY, MURF_API_URL, ASSEMBLYAI_API_KEY, GOOGLE_API_KEY

### 2. Error Scenarios Testing

-   **Endpoint**: `/test/errors`
-   **Purpose**: Test different failure scenarios
-   **Shows**: Which services are working vs missing API keys
-   **Includes**: Fallback message generation

### 3. Agent Chat Error Handling (/agent/chat/{session_id})

#### Speech-to-Text (STT) Error Handling:

-   **Graceful Failure**: When AssemblyAI API fails
-   **Fallback**: Uses placeholder message "I'm having trouble understanding the audio"
-   **Logging**: Detailed error logging for debugging

#### Large Language Model (LLM) Error Handling:

-   **Graceful Failure**: When Google Generative AI fails
-   **Fallback**: Contextual error messages based on which other services failed
-   **Dynamic Response**: Different messages for single vs multiple service failures

#### Text-to-Speech (TTS) Error Handling:

-   **Graceful Failure**: When MurfAI API fails
-   **Fallback**: Client-side browser TTS as backup
-   **Timeout Handling**: 30-second request timeout for TTS calls

#### Combined Error Scenarios:

-   **Multiple Failures**: Handles combinations of STT, LLM, and TTS failures
-   **Error Reporting**: Detailed error information in response
-   **Fallback Messages**: Contextual messages based on failure combinations

### 4. Error Response Structure

```json
{
    "session_id": "session_123",
    "audio_url": null,
    "user_message": "transcribed text or fallback",
    "assistant_response": "AI response or fallback message",
    "chat_history_length": 2,
    "input_type": "audio",
    "errors": {
        "transcription_error": "error details or null",
        "llm_error": "error details or null",
        "tts_error": "error details or null"
    }
}
```

## Client-Side Error Handling (script.js)

### 1. Browser Compatibility Checks

-   **Media Devices API**: Checks for microphone access
-   **MediaRecorder**: Verifies recording capability
-   **Speech Synthesis**: Checks for fallback TTS support
-   **User Feedback**: Clear error messages for missing features

### 2. Server Health Monitoring

-   **Automatic Check**: Tests server health on page load
-   **Status Display**: Shows degraded status warnings
-   **Missing API Keys**: Alerts user to service limitations

### 3. Recording Error Handling

-   **Permission Denied**: Clear instructions for microphone access
-   **Device Unavailable**: Fallback instructions and UI state management
-   **Button State**: Disables recording controls when microphone unavailable

### 4. Network Error Handling

-   **Timeout Protection**: 30-second request timeout
-   **Connection Failures**: Distinguishes between network and server errors
-   **Retry Guidance**: User-friendly error messages with retry suggestions

### 5. Fallback Text-to-Speech

-   **Browser TTS**: Uses Web Speech API when server TTS fails
-   **Voice Selection**: Attempts to use appropriate Indian English voices
-   **Error Recovery**: Graceful fallback when both server and browser TTS fail

### 6. Progress Tracking & User Feedback

-   **Real-time Updates**: Shows processing stages (Recording → Processing → Playing)
-   **Error States**: Color-coded status indicators (success/warning/error)
-   **Detailed Messages**: Specific error descriptions for troubleshooting

## Error Scenarios Tested

### 1. All APIs Working

-   Status: `healthy`
-   Behavior: Full functionality with server-generated TTS

### 2. Google API Key Missing (LLM Failure)

-   Status: `degraded`
-   Behavior: Shows fallback message "I'm having trouble processing your request"
-   TTS: Still works for fallback message

### 3. AssemblyAI Key Missing (STT Failure)

-   Status: `degraded`
-   Behavior: Uses placeholder for transcription, LLM and TTS still work
-   Message: "I'm having trouble understanding the audio"

### 4. MurfAI Key Missing (TTS Failure)

-   Status: `degraded`
-   Behavior: STT and LLM work, uses browser TTS for playback
-   Fallback: Web Speech API with Indian English voice preference

### 5. Multiple Service Failures

-   Status: `degraded`
-   Behavior: Combines appropriate fallback messages
-   Example: "I'm having trouble with both understanding your audio and processing requests"

### 6. All Services Fail

-   Status: `degraded`
-   Behavior: Complete fallback mode with browser TTS
-   Message: "I'm experiencing technical difficulties with all my services"

## Testing Instructions

1. **Start Server**: Run `python start_server.py`
2. **Check Health**: Visit `http://localhost:8000/health`
3. **Test Errors**: Visit `http://localhost:8000/test/errors`
4. **Simulate Failures**: Comment out API keys in `.env` file
5. **Test Recording**: Use the web interface to test voice recording

## Key Benefits

1. **Zero Downtime**: Application continues working even with service failures
2. **User Experience**: Clear feedback about what's working/not working
3. **Debugging Support**: Detailed error logging and testing endpoints
4. **Graceful Degradation**: Smart fallback strategies for each component
5. **Robust Client**: Handles network issues, timeouts, and browser compatibility
6. **Recovery Options**: Automatic fallback to browser-based features when possible

## Files Modified

-   `run.py`: Enhanced error handling for all API endpoints
-   `static/script.js`: Comprehensive client-side error handling
-   `start_server.py`: Improved server startup with error handling
-   `.env`: API key configuration for testing scenarios
