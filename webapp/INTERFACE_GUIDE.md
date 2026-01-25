# V.E.D.A.M.A.X. Interface Guide

## Interface Overview

V.E.D.A.M.A.X. features a modern, Gemini-inspired interface with a clean, professional design optimized for medical document analysis.

## Layout Structure

### Main Header
- **Title**: "🩺 V.E.D.A.M.A.X." with gradient purple/blue styling
- **Subtitle**: "Vectorized Empathetic Data Assistant for Maximum Analytic Extraction"
- Centered, prominent display at the top

### Sidebar (Left Panel)
- **Logo & Branding**: V.E.D.A.M.A.X. branding with subtitle
- **Quick Actions**:
  - 🔄 New Chat button
  - 📊 View Documents button
- **Statistics Dashboard**:
  - Document count metric
  - Chat count metric
- **Settings**:
  - Chunking Strategy selector (semantic/token)
  - Enable OCR checkbox
- **About Section**: Brief description of capabilities
- **Footer**: Version and copyright info

### Main Content Area

#### Tab 1: 💬 Chat Interface
- **Welcome Message**: When no messages exist, shows:
  - Welcome greeting
  - List of capabilities
  - Call-to-action to upload or ask questions
- **Chat Messages**:
  - **User Messages**: Right-aligned, purple gradient background, rounded corners
  - **Assistant Messages**: Left-aligned, light gray background, purple left border
  - Source citations expandable for assistant messages
- **Input Area**:
  - Large text input with rounded corners
  - Send button with gradient styling
  - Placeholder: "Ask V.E.D.A.M.A.X. about your medical documents..."

#### Tab 2: 📄 Documents Interface
- **Upload Section**:
  - File uploader supporting PDF, DOCX, DOC, PNG, JPG, JPEG
  - Drag-and-drop interface
  - Multiple file selection
- **Uploaded Files Display**:
  - File cards showing:
    - File name with icon
    - File size
    - File type
    - Visual file type indicator
- **Process Button**: Large, prominent button to process all uploaded files
- **Processed Documents List**:
  - Expandable cards for each processed document
  - Status indicators (success/error)
  - Processing metadata
  - Chunk count information

## Design Features

### Color Scheme
- **Primary Gradient**: Purple to Blue (#667eea to #764ba2)
- **Background**: Clean white with light gray accents
- **Text**: Dark gray (#1f2937) for readability
- **Accents**: Purple borders and highlights

### Typography
- **Headers**: Bold, large font sizes
- **Body**: Clean, readable sans-serif
- **Subtitles**: Medium gray for secondary information

### Interactive Elements
- **Buttons**: Rounded, gradient backgrounds with hover effects
- **Input Fields**: Rounded corners, purple focus borders
- **Cards**: Subtle shadows, hover lift effects
- **Scrollbars**: Custom styled, purple theme

### Responsive Design
- Wide layout optimized for desktop
- Sidebar can be collapsed
- Content adapts to screen size

## User Flow

1. **Initial State**: User sees welcome message in chat
2. **Upload Documents**: User navigates to Documents tab, uploads files
3. **Process Documents**: User clicks "Process Documents" button
4. **View Results**: Processed documents appear in list
5. **Ask Questions**: User returns to Chat tab, asks questions about documents
6. **Get Responses**: V.E.D.A.M.A.X. provides empathetic, clinically-grounded answers

## Key Visual Elements

- **Gradient Headers**: Eye-catching purple-blue gradients
- **Rounded Corners**: Modern, friendly appearance
- **Card-Based Layout**: Clean separation of content
- **Status Indicators**: Color-coded (green=success, yellow=processing, red=error)
- **Icons**: Emoji-based for friendly, approachable feel
- **Smooth Animations**: Subtle hover and transition effects

## Accessibility Features

- High contrast text
- Clear visual hierarchy
- Intuitive navigation
- Helpful tooltips
- Error messages with clear explanations

