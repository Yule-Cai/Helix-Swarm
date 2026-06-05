# ASL Virtual Human Technical Architecture Document

> **Version**: 1.0.0  
> **Date**: January 2025  
> **Status**: Draft  
> **Target Publication**: JHCI (Journal of Human-Computer Interaction)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Data Pipeline](#4-data-pipeline)
5. [Two-Hand Modeling Approach](#5-two-hand-modeling-approach)
6. [User Study Design](#6-user-study-design)
7. [Project Structure](#7-project-structure)
8. [Implementation Phases](#8-implementation-phases)
9. [Key Technical Challenges](#9-key-technical-challenges)
10. [Evaluation Metrics](#10-evaluation-metrics)
11. [API Specifications](#11-api-specifications)
12. [Performance Requirements](#12-performance-requirements)
13. [Security Considerations](#13-security-considerations)
14. [References](#14-references)

---

## 1. Executive Summary

### 1.1 Project Vision

The ASL Virtual Human project aims to create a web-based virtual human capable of translating text and voice input into American Sign Language (ASL) animations. This system bridges the communication gap between hearing and deaf communities by leveraging Large Language Models (LLMs) for English-to-ASL gloss translation and advanced 3D animation techniques for realistic sign language rendering.

### 1.2 Key Innovations

| Innovation | Description | Impact |
|------------|-------------|--------|
| **LLM-based Translation** | GPT-4/Claude for English→ASL gloss conversion | Higher accuracy than rule-based systems |
| **Two-Hand Collaborative Modeling** | Independent hand control with collision avoidance | More natural signing appearance |
| **Deaf User Participation** | Community-driven evaluation and feedback | Culturally appropriate and intelligible output |
| **Web-Based Deployment** | Three.js rendering in browser | Zero-installation accessibility |

### 1.3 Research Contributions

1. **Novel Translation Pipeline**: LLM-based English→ASL gloss with non-manual marker generation
2. **Two-Hand Animation System**: Collaborative hand modeling with physics-based collision avoidance
3. **Community-Centered Evaluation**: Deaf community participation in design and evaluation
4. **Open-Source Framework**: Reusable ASL animation generation system

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ASL VIRTUAL HUMAN SYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                           INPUT LAYER                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │ Text Input   │  │ Voice Input │  │ File Upload │  │ API Input   │   │  │
│  │  │ (React UI)   │  │ (Web Speech │  │ (Documents) │  │ (REST/WS)   │   │  │
│  │  │              │  │  API/Whisper)│  │             │  │             │   │  │
│  │  └──────┬───────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │  │
│  └─────────┼─────────────────┼────────────────┼────────────────┼───────────┘  │
│            │                 │                │                │               │
│            ▼                 ▼                ▼                ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                      NLP / TRANSLATION LAYER                             │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                    LLM Translation Engine                        │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Text         │  │ ASL Grammar  │  │ Non-Manual Marker    │  │    │  │
│  │  │  │ Preprocessor │→ │ Converter    │→ │ Generator            │  │    │  │
│  │  │  │              │  │ (GPT-4/Claude)│  │ (Facial Expressions) │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                          │  │
│  │                              ▼                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                    ASL Gloss Dictionary                          │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Sign Database │  │ Animation    │  │ Transition Rules     │  │    │  │
│  │  │  │ (ASLLVD/WLASL)│  │ Mappings     │  │ (Blending Params)    │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                          │
│                                    ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                    ANIMATION GENERATION LAYER                            │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                 Animation Controller                             │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Skeletal     │  │ Two-Hand     │  │ Animation Blending   │  │    │  │
│  │  │  │ Animation    │  │ Coordinator  │  │ Engine               │  │    │  │
│  │  │  │ System       │  │              │  │                      │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                          │  │
│  │                              ▼                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                 Physics & Collision System                       │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Hand         │  │ Collision    │  │ Inverse Kinematics   │  │    │  │
│  │  │  │ Independence │  │ Detection    │  │ Solver               │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                          │
│                                    ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                       3D RENDERING LAYER                                 │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                    Three.js Renderer                             │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Scene        │  │ Avatar       │  │ Lighting &           │  │    │  │
│  │  │  │ Management   │  │ Loading      │  │ Environment          │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                          │  │
│  │                              ▼                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                    Post-Processing                               │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Shadows      │  │ Anti-aliasing│  │ Performance          │  │    │  │
│  │  │  │ & Reflections│  │ & Effects    │  │ Optimization         │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                          │
│                                    ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                       USER STUDY MODULE                                  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                    Evaluation Framework                          │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Intelligibility│ Naturalness  │  │ User Satisfaction    │  │    │  │
│  │  │  │ Assessment   │  │ Rating       │  │ Survey               │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  │                              │                                          │  │
│  │                              ▼                                          │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐    │  │
│  │  │                    Data Collection                               │    │  │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │    │  │
│  │  │  │ Interaction  │  │ Feedback     │  │ Analytics            │  │    │  │
│  │  │  │ Logging      │  │ Collection   │  │ Dashboard            │  │    │  │
│  │  │  └──────────────┘  └──────────────┘  └──────────────────────┘  │    │  │
│  │  └─────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Interaction Flow

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │────▶│   Input     │────▶│ Translation │────▶│  Animation  │
│  Input  │     │  Processing │     │    (LLM)    │     │  Generation │
└─────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                               │
                                                               ▼
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │◀────│  Rendering  │◀────│   Physics   │◀────│   Two-Hand  │
│ Output  │     │  (Three.js) │     │   System    │     │  Coordination│
└─────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### 2.3 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW DIAGRAM                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │  English  │───▶│   Text   │───▶│   ASL    │───▶│  Gloss   │         │
│  │   Text    │    │   Clean  │    │  Gloss   │    │ Sequence │         │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘         │
│                                                       │                │
│                                                       ▼                │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│  │  Rendered│◀───│  Three.js│◀───│ Skeletal │◀───│ Animation│         │
│  │  Output  │    │  Scene   │    │  Pose    │    │  Data    │         │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technology Stack

### 3.1 Frontend Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **UI Framework** | React | 18.x | Component-based UI |
| **Language** | TypeScript | 5.x | Type safety |
| **3D Rendering** | Three.js | r160+ | WebGL 3D graphics |
| **3D Integration** | React Three Fiber | 8.x | React bindings for Three.js |
| **State Management** | Zustand | 4.x | Lightweight state management |
| **Styling** | Tailwind CSS | 3.x | Utility-first CSS |
| **Build Tool** | Vite | 5.x | Fast development builds |
| **Testing** | Vitest + Testing Library | Latest | Unit & integration tests |
| **Voice Input** | Web Speech API | Native | Browser speech recognition |
| **HTTP Client** | Axios | 1.x | API communication |
| **WebSocket** | Socket.io Client | 4.x | Real-time communication |

### 3.2 Backend Stack

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Framework** | FastAPI | 0.100+ | Async Python web framework |
| **Language** | Python | 3.11+ | Backend logic |
| **LLM Integration** | OpenAI API / Anthropic | Latest | GPT-4 / Claude integration |
| **ASR** | OpenAI Whisper | Latest | Speech-to-text |
| **Database** | PostgreSQL | 15+ | Persistent storage |
| **Cache** | Redis | 7.x | Caching & sessions |
| **ORM** | SQLAlchemy | 2.x | Database operations |
| **Task Queue** | Celery | 5.x | Async task processing |
| **Testing** | Pytest | 7.x | Backend testing |
| **API Docs** | OpenAPI/Swagger | 3.0 | API documentation |

### 3.3 3D & Animation Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Avatar System** | Ready Player Me | Customizable 3D avatars |
| **Animation Library** | Mixamo | Pre-built animations |
| **Hand Rigging** | Custom FBX | Detailed hand bones |
| **Animation Format** | glTF 2.0 | Web-optimized 3D format |
| **Physics** | Cannon.js / Rapier | Collision detection |
| **Inverse Kinematics** | Three.js IK | Hand positioning |

### 3.4 DevOps & Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Containerization** | Docker | Consistent environments |
| **Orchestration** | Docker Compose | Local development |
| **CI/CD** | GitHub Actions | Automated pipelines |
| **Hosting** | Vercel (Frontend) / AWS (Backend) | Production deployment |
| **Monitoring** | Sentry | Error tracking |
| **Analytics** | PostHog | User analytics |

---

## 4. Data Pipeline

### 4.1 ASL Gloss Dictionary Structure

```json
{
  "gloss_database": {
    "version": "1.0.0",
    "last_updated": "2025-01-XX",
    "signs": {
      "HELLO": {
        "id": "sign_001",
        "gloss": "HELLO",
        "english_equivalent": ["hello", "hi", "greetings"],
        "handshape": {
          "dominant": "B-flat",
          "non_dominant": null
        },
        "location": {
          "area": "neutral-space",
          "specific": "shoulder-height"
        },
        "movement": {
          "type": "wave",
          "direction": "forward",
          "repetition": 1
        },
        "non_manual_markers": {
          "facial_expression": "smile",
          "mouth_movement": "open",
          "eye_gaze": "forward",
          "head_movement": "slight-nod"
        },
        "animation_file": "animations/hello.glb",
        "duration_ms": 1200,
        "transition_points": {
          "start": {
            "right_hand": [0, 0, 0],
            "left_hand": [0, 0, 0]
          },
          "end": {
            "right_hand": [0.3, 0.5, 0],
            "left_hand": [0, 0, 0]
          }
        },
        "frequency_rank": 15,
        "difficulty": "beginner",
        "tags": ["greeting", "common", "daily"]
      }
    },
    "transitions": {
      "HELLO_TO_NAME": {
        "from": "HELLO",
        "to": "NAME",
        "blend_duration_ms": 300,
        "blend_type": "linear",
        "intermediate_poses": []
      }
    },
    "finger_spell_alphabet": {
      "A": { "animation_file": "animations/fingerspell/a.glb" },
      "B": { "animation_file": "animations/fingerspell/b.glb" },
      // ... all 26 letters
    }
  }
}
```

### 4.2 LLM Translation Pipeline

```python
# English to ASL Gloss Translation Prompt Template

TRANSLATION_SYSTEM_PROMPT = """
You are an expert ASL (American Sign Language) translator. Your task is to convert 
English text into ASL gloss notation.

ASL Grammar Rules:
1. ASL uses Topic-Comment structure (not SVO like English)
2. Time indicators come first in the sentence
3. Questions use non-manual markers (raised eyebrows for yes/no, 
   furrowed brows for wh-questions)
4. Pronouns are indicated by spatial reference
5. Negation uses head shake
6. Classifiers represent categories of objects

Output Format:
Return a JSON object with:
- gloss_sequence: Array of ASL gloss signs
- non_manual_markers: Facial expressions and body movements
- spatial_references: Pronoun and location mappings
- time_markers: Temporal indicators
- confidence: Translation confidence score (0-1)

Example:
Input: "My name is John and I am happy to meet you."
Output: {
  "gloss_sequence": ["ME", "NAME", "J-O-H-N", "HAPPY", "MEET", "YOU"],
  "non_manual_markers": {
    "0": { "expression": "neutral" },
    "3": { "expression": "smile" },
    "4": { "expression": "smile", "head_nod": true }
  },
  "spatial_references": {
    "ME": "chest-point",
    "YOU": "forward-point"
  },
  "time_markers": [],
  "confidence": 0.92
}
"""

TRANSLATION_USER_PROMPT = """
Convert the following English text to ASL gloss:

English: {english_text}

Context: {context}
Register: {register}  # formal/informal
Speed: {speed}  # normal/slow/fast
```

### 4.3 Animation Blending Algorithm

```typescript
// Animation blending for smooth transitions between signs

interface AnimationBlendConfig {
  blendDuration: number;      // milliseconds
  blendType: 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out' | 'cubic';
  weight: number;             // 0-1, influence of target animation
  boneMask?: string[];        // specific bones to blend
}

class AnimationBlender {
  private currentPose: SkeletonPose;
  private targetPose: SkeletonPose;
  private blendProgress: number = 0;
  
  blend(
    from: SkeletonPose,
    to: SkeletonPose,
    config: AnimationBlendConfig
  ): SkeletonPose {
    const t = this.easeFunction(this.blendProgress, config.blendType);
    
    const blendedPose = new SkeletonPose();
    
    for (const bone of from.bones) {
      if (config.boneMask && !config.boneMask.includes(bone.name)) {
        blendedPose.setBone(bone.name, from.getBone(bone.name));
        continue;
      }
      
      const fromBone = from.getBone(bone.name);
      const toBone = to.getBone(bone.name);
      
      // Quaternion SLERP for rotation
      blendedPose.setBone(bone.name, {
        position: this.lerp(fromBone.position, toBone.position, t),
        rotation: this.slerp(fromBone.rotation, toBone.rotation, t),
        scale: this.lerp(fromBone.scale, toBone.scale, t)
      });
    }
    
    return blendedPose;
  }
  
  private easeFunction(t: number, type: string): number {
    switch (type) {
      case 'linear': return t;
      case 'ease-in': return t * t;
      case 'ease-out': return t * (2 - t);
      case 'ease-in-out': return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      case 'cubic': return t * t * (3 - 2 * t);
      default: return t;
    }
  }
  
  private lerp(a: Vector3, b: Vector3, t: number): Vector3 {
    return new Vector3(
      a.x + (b.x - a.x) * t,
      a.y + (b.y - a.y) * t,
      a.z + (b.z - a.z) * t
    );
  }
  
  private slerp(a: Quaternion, b: Quaternion, t: number): Quaternion {
    return new Quaternion().slerpQuaternions(a, b, t);
  }
}
```

---

## 5. Two-Hand Modeling Approach

### 5.1 Hand Independence System

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TWO-HAND COORDINATION SYSTEM                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Hand Controller Manager                       │   │
│  │  ┌─────────────────────┐     ┌─────────────────────┐           │   │
│  │  │   Dominant Hand     │     │  Non-Dominant Hand  │           │   │
│  │  │   (Right)           │     │  (Left)             │           │   │
│  │  │  ┌───────────────┐  │     │  ┌───────────────┐  │           │   │
│  │  │  │ Finger IK     │  │     │  │ Finger IK     │  │           │   │
│  │  │  │ Solver        │  │     │  │ Solver        │  │           │   │
│  │  │  └───────────────┘  │     │  └───────────────┘  │           │   │
│  │  │  ┌───────────────┐  │     │  ┌───────────────┐  │           │   │
│  │  │  │ Wrist         │  │     │  │ Wrist         │  │           │   │
│  │  │  │ Controller    │  │     │  │ Controller    │  │           │   │
│  │  │  └───────────────┘  │     │  └───────────────┘  │           │   │
│  │  └─────────────────────┘     └─────────────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Collision Avoidance System                    │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │ Bounding Box  │  │ Distance      │  │ Penetration   │       │   │
│  │  │ Detection     │  │ Calculation   │  │ Resolution    │       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                    │
│                                    ▼                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Synchronization Engine                        │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │ Temporal      │  │ Spatial       │  │ Priority      │       │   │
│  │  │ Sync          │  │ Alignment     │  │ Management    │       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Collision Avoidance Algorithm

```typescript
// Two-hand collision avoidance system

interface HandBone {
  name: string;
  position: Vector3;
  boundingSphere: { center: Vector3; radius: number };
}

class CollisionAvoidanceSystem {
  private dominantHand: HandBone[];
  private nonDominantHand: HandBone[];
  private minDistance: number = 0.02; // 2cm minimum distance
  
  checkCollision(): CollisionResult {
    const collisions: Collision[] = [];
    
    for (const dominantBone of this.dominantHand) {
      for (const nonDominantBone of this.nonDominantHand) {
        const distance = dominantBone.position.distanceTo(
          nonDominantBone.position
        );
        
        if (distance < this.minDistance) {
          collisions.push({
            bone1: dominantBone.name,
            bone2: nonDominantBone.name,
            penetration: this.minDistance - distance,
            contactPoint: this.calculateContactPoint(
              dominantBone, nonDominantBone
            )
          });
        }
      }
    }
    
    return {
      hasCollision: collisions.length > 0,
      collisions,
      resolution: this.resolveCollisions(collisions)
    };
  }
  
  resolveCollisions(collisions: Collision[]): HandAdjustment[] {
    return collisions.map(collision => {
      const direction = this.calculatePushDirection(collision);
      const magnitude = collision.penetration * 1.1; // 10% buffer
      
      // Non-dominant hand yields to dominant hand
      return {
        hand: 'non-dominant',
        adjustment: direction.multiplyScalar(magnitude),
        priority: 1
      };
    });
  }
}
```

### 5.3 Hand Pose Classification

```typescript
// ASL handshape classification system

enum HandshapeGroup {
  // Group 1: Fist variations
  A = 'A', S = 'S', T = 'T', M = 'M', N = 'N', E = 'E',
  
  // Group 2: Flat hand variations
  B = 'B', C = 'C', O = 'O', 
  FLAT_B = 'FLAT_B', BENT_B = 'BENT_B',
  
  // Group 3: Pointing
  INDEX = 'INDEX', D = 'D', POINT_1 = '1',
  
  // Group 4: Hook
  HOOK = 'HOOK', OPEN_8 = 'OPEN_8',
  
  // Group 5: V-shapes
  V = 'V', K = 'K', P = 'P', 
  THREE = '3', U = 'U', 
  V_BENT = 'V_BENT',
  
  // Group 6: Ring
  F = 'F', OPEN_9 = 'OPEN_9',
  
  // Group 7: Pinky
  I = 'I', Y = 'Y', 
  HANG_LOOSE = 'HANG_LOOSE',
  
  // Group 8: Thumb
  G = 'G', H = 'H', 
  THUMB_UP = 'THUMB_UP',
  
  // Group 9: Complex
  R = 'R', W = 'W', 
  DOUBLE_HOOK = 'DOUBLE_HOOK',
  
  // Group 10: Spread
  OPEN_A = 'OPEN_A', 
  SPREAD_5 = '5', 
  FLAT_O = 'FLAT_O',
  
  // Special
  RELAXED = 'RELAXED',
  NEUTRAL = 'NEUTRAL'
}

interface HandshapeConfig {
  group: HandshapeGroup;
  fingers: {
    thumb: FingerConfig;
    index: FingerConfig;
    middle: FingerConfig;
    ring: FingerConfig;
    pinky: FingerConfig;
  };
  palmOrientation: Quaternion;
  wristAngle: number;
}

interface FingerConfig {
  curl: number;        // 0 = straight, 1 = fully curled
  spread: number;      // 0 = together, 1 = fully spread
  side: 'neutral' | 'left' | 'right';  // lateral deviation
}
```

---

## 6. User Study Design

### 6.1 Recruitment Strategy

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DEAF COMMUNITY RECRUITMENT PLAN                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: Community Partnership (Weeks 1-4)                            │
│  ├── Contact local Deaf organizations                                  │
│  ├── Partner with Gallaudet University                                 │
│  ├── Connect with National Association of the Deaf (NAD)               │
│  └── Engage Deaf community leaders as advisors                         │
│                                                                         │
│  Phase 2: Participant Recruitment (Weeks 5-8)                          │
│  ├── Target: 30-50 Deaf ASL users                                      │
│  ├── Age range: 18-65                                                  │
│  ├── ASL proficiency: Native or near-native                            │
│  ├── Mix of educational backgrounds                                    │
│  └── Compensation: $50-75 per session                                  │
│                                                                         │
│  Phase 3: Screening (Weeks 9-10)                                       │
│  ├── ASL proficiency assessment                                        │
│  ├── Technology comfort survey                                         │
│  ├── Demographic questionnaire                                         │
│  └── Informed consent process                                          │
│                                                                         │
│  Recruitment Channels:                                                  │
│  ├── Deaf schools and programs                                         │
│  ├── ASL interpreter training programs                                 │
│  ├── Deaf social media groups                                          │
│  ├── Deaf community events                                             │
│  └── University disability services                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Evaluation Protocol

```yaml
# User Study Evaluation Protocol

study_design:
  type: "within-subjects"
  conditions:
    - name: "LLM-based ASL"
      description: "Our system with LLM translation"
    - name: "Rule-based ASL"
      description: "Traditional rule-based translation"
    - name: "Human Baseline"
      description: "Video recordings of human signers"
  
  randomization: "latin-square"
  counterbalancing: true

tasks:
  - id: "task_1"
    name: "Sentence Comprehension"
    description: "Watch signed sentences and identify meaning"
    type: "comprehension"
    items: 20
    time_limit: "30 seconds per item"
    
  - id: "task_2"
    name: "Sign Identification"
    description: "Identify individual signs from animations"
    type: "recognition"
    items: 50
    time_limit: "15 seconds per item"
    
  - id: "task_3"
    name: "Free Response"
    description: "Describe what the avatar is signing"
    type: "open-ended"
    items: 10
    time_limit: "60 seconds per item"

metrics:
  primary:
    - name: "Intelligibility Score"
      type: "percentage"
      calculation: "correct_identifications / total_items * 100"
      
    - name: "Naturalness Rating"
      type: "likert_7"
      anchors: ["Very Unnatural", "Very Natural"]
      
  secondary:
    - name: "Response Time"
      type: "milliseconds"
      calculation: "time_from_animation_end_to_response"
      
    - name: "Confidence Rating"
      type: "likert_5"
      anchors: ["Not Confident", "Very Confident"]
      
    - name: "User Satisfaction"
      type: "likert_7"
      anchors: ["Very Dissatisfied", "Very Satisfied"]

questionnaires:
  pre_study:
    - "Demographic Information"
    - "ASL Proficiency Self-Assessment"
    - "Technology Experience Survey"
    
  post_task:
    - "NASA Task Load Index (TLX)"
    - "System Usability Scale (SUS)"
    
  post_study:
    - "Overall Satisfaction Survey"
    - "Open-ended Feedback"
    - "Comparison with Other Systems"
```

### 6.3 IRB Considerations

```markdown
## IRB Protocol Summary

### Study Title
"Evaluation of LLM-Based ASL Virtual Human for Accessibility"

### Risk Assessment
- **Risk Level**: Minimal Risk
- **Vulnerable Population**: Deaf/Hard of Hearing individuals
- **Data Sensitivity**: Video recordings, demographic data

### Informed Consent Requirements
1. Written consent in plain language
2. ASL video consent option
3. Right to withdraw at any time
4. Data storage and privacy protection
5. Compensation disclosure

### Accessibility Measures
- All materials in ASL and English
- Certified ASL interpreters present
- Visual instructions and demonstrations
- Captioned video content
- Flexible scheduling

### Data Protection
- De-identification of all data
- Secure storage (encrypted)
- Limited access (research team only)
- Retention period: 5 years
- Destruction protocol after retention

### Compensation
- $50 per in-person session
- $25 per remote session
- Additional $25 for follow-up interview
- Payment via gift card or direct deposit
```

---

## 7. Project Structure

### 7.1 Complete Directory Structure

```
asl-virtual-human/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # Main CI pipeline
│   │   ├── cd.yml                    # Deployment pipeline
│   │   ├── test.yml                  # Test pipeline
│   │   └── security.yml              # Security scanning
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── user_study_feedback.md
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/
│   ├── api/
│   │   ├── openapi.yaml              # API specification
│   │   └── websocket.md              # WebSocket protocol
│   ├── architecture/
│   │   ├── system-overview.md
│   │   ├── data-pipeline.md
│   │   └── animation-system.md
│   ├── guides/
│   │   ├── getting-started.md
│   │   ├── development.md
│   │   ├── deployment.md
│   │   └── user-study.md
│   ├── plans/
│   │   ├── 2025-01-XX-asl-virtual-human-architecture.md  # This document
│   │   ├── phase-1-prototype.md
│   │   ├── phase-2-llm-integration.md
│   │   ├── phase-3-two-hand.md
│   │   └── phase-4-user-study.md
│   └── research/
│       ├── literature-review.md
│       ├── asl-grammar-notes.md
│       └── related-work.md
│
├── frontend/
│   ├── public/
│   │   ├── models/
│   │   │   ├── avatars/
│   │   │   │   ├── male-01.glb
│   │   │   │   ├── female-01.glb
│   │   │   │   └── ...
│   │   │   ├── animations/
│   │   │   │   ├── signs/
│   │   │   │   │   ├── hello.glb
│   │   │   │   │   ├── goodbye.glb
│   │   │   │   │   └── ...
│   │   │   │   ├── fingerspell/
│   │   │   │   │   ├── a.glb
│   │   │   │   │   ├── b.glb
│   │   │   │   │   └── ...
│   │   │   │   └── transitions/
│   │   │   │       └── ...
│   │   │   └── environments/
│   │   │       ├── classroom.glb
│   │   │       └── neutral.glb
│   │   ├── textures/
│   │   │   ├── skin/
│   │   │   └── clothing/
│   │   └── sounds/
│   │       └── feedback/
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── providers.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Modal.tsx
│   │   │   │   ├── Slider.tsx
│   │   │   │   └── ...
│   │   │   │
│   │   │   ├── avatar/
│   │   │   │   ├── AvatarScene.tsx        # Main 3D scene
│   │   │   │   ├── AvatarModel.tsx        # Avatar loading
│   │   │   │   ├── HandController.tsx     # Hand animation
│   │   │   │   ├── FacialExpression.tsx   # Face animation
│   │   │   │   ├── AnimationPlayer.tsx    # Animation playback
│   │   │   │   └── CameraControls.tsx     # Camera management
│   │   │   │
│   │   │   ├── input/
│   │   │   │   ├── TextInput.tsx          # Text input
│   │   │   │   ├── VoiceInput.tsx         # Voice recording
│   │   │   │   ├── FileUpload.tsx         # Document upload
│   │   │   │   └── InputSelector.tsx      # Input method switch
│   │   │   │
│   │   │   ├── translation/
│   │   │   │   ├── TranslationPanel.tsx   # Translation display
│   │   │   │   ├── GlossViewer.tsx        # ASL gloss display
│   │   │   │   └── ConfidenceIndicator.tsx
│   │   │   │
│   │   │   └── study/
│   │   │       ├── StudyConsent.tsx       # Consent form
│   │   │       ├── TaskPresenter.tsx      # Study tasks
│   │   │       ├── FeedbackForm.tsx       # User feedback
│   │   │       └── ResultsDashboard.tsx   # Study results
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAvatar.ts              # Avatar management
│   │   │   ├── useAnimation.ts           # Animation control
│   │   │   ├── useTranslation.ts         # Translation API
│   │   │   ├── useVoiceInput.ts          # Voice recognition
│   │   │   ├── useHandTracking.ts        # Hand pose tracking
│   │   │   └── useStudySession.ts        # Study management
│   │   │
│   │   ├── services/
│   │   │   ├── api/
│   │   │   │   ├── translationApi.ts     # Translation endpoints
│   │   │   │   ├── animationApi.ts       # Animation endpoints
│   │   │   │   └── studyApi.ts           # Study endpoints
│   │   │   │
│   │   │   ├── three/
│   │   │   │   ├── SceneManager.ts       # Three.js scene
│   │   │   │   ├── AnimationMixer.ts     # Animation mixing
│   │   │   │   ├── PhysicsEngine.ts      # Collision detection
│   │   │   │   └── PostProcessing.ts     # Visual effects
│   │   │   │
│   │   │   └── audio/
│   │   │       ├── SpeechRecognition.ts  # Web Speech API
│   │   │       └── AudioProcessor.ts     # Audio processing
│   │   │
│   │   ├── stores/
│   │   │   ├── avatarStore.ts            # Avatar state
│   │   │   ├── translationStore.ts       # Translation state
│   │   │   ├── animationStore.ts         # Animation state
│   │   │   └── studyStore.ts             # Study state
│   │   │
│   │   ├── types/
│   │   │   ├── avatar.ts                 # Avatar types
│   │   │   ├── animation.ts              # Animation types
│   │   │   ├── translation.ts            # Translation types
│   │   │   ├── gloss.ts                  # ASL gloss types
│   │   │   └── study.ts                  # Study types
│   │   │
│   │   ├── utils/
│   │   │   ├── math/
│   │   │   │   ├── quaternion.ts         # Quaternion math
│   │   │   │   ├── vector.ts             # Vector operations
│   │   │   │   └── interpolation.ts      # Interpolation utils
│   │   │   │
│   │   │   ├── animation/
│   │   │   │   ├── blender.ts            # Animation blending
│   │   │   │   ├── easing.ts             # Easing functions
│   │   │   │   └── retargeting.ts        # Animation retargeting
│   │   │   │
│   │   │   └── asl/
│   │   │       ├── handshapes.ts         # Handshape definitions
│   │   │       ├── locations.ts          # Signing locations
│   │   │       └── transitions.ts        # Transition rules
│   │   │
│   │   └── styles/
│   │       ├── globals.css
│   │       └── components/
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   └── utils/
│   │   ├── integration/
│   │   │   ├── avatar.test.tsx
│   │   │   └── translation.test.tsx
│   │   └── e2e/
│   │       ├── translation-flow.spec.ts
│   │       └── study-flow.spec.ts
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── .eslintrc.js
│   └── .prettierrc
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # FastAPI application
│   │   ├── config.py                   # Configuration
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── translation.py  # Translation endpoints
│   │   │   │   │   ├── animation.py    # Animation endpoints
│   │   │   │   │   ├── gloss.py        # Gloss database endpoints
│   │   │   │   │   ├── study.py        # User study endpoints
│   │   │   │   │   └── health.py       # Health check
│   │   │   │   └── router.py           # API router
│   │   │   └── deps.py                 # Dependencies
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py             # Authentication
│   │   │   ├── exceptions.py           # Custom exceptions
│   │   │   └── logging.py              # Logging configuration
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── gloss.py                # Gloss data models
│   │   │   ├── animation.py            # Animation models
│   │   │   ├── translation.py          # Translation models
│   │   │   └── study.py                # Study models
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── translation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── llm_service.py      # LLM integration
│   │   │   │   ├── gloss_converter.py  # English to gloss
│   │   │   │   ├── grammar_processor.py# ASL grammar
│   │   │   │   └── nmm_generator.py    # Non-manual markers
│   │   │   │
│   │   │   ├── animation/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── animation_service.py# Animation management
│   │   │   │   ├── hand_controller.py  # Hand control
│   │   │   │   ├── collision_system.py # Collision detection
│   │   │   │   └── blender.py          # Animation blending
│   │   │   │
│   │   │   ├── audio/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── speech_recognition.py# ASR service
│   │   │   │   └── audio_processor.py  # Audio processing
│   │   │   │
│   │   │   └── study/
│   │   │       ├── __init__.py
│   │   │       ├── study_manager.py    # Study management
│   │   │       ├── data_collector.py   # Data collection
│   │   │       └── analytics.py        # Study analytics
│   │   │
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── session.py              # Database session
│   │   │   ├── base.py                 # Base model
│   │   │   └── migrations/             # Alembic migrations
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── gloss_parser.py         # Gloss parsing
│   │       ├── animation_utils.py      # Animation utilities
│   │       └── validators.py           # Input validation
│   │
│   ├── data/
│   │   ├── gloss_database.json         # ASL gloss dictionary
│   │   ├── animations/                 # Animation files
│   │   ├── prompts/                    # LLM prompts
│   │   │   ├── translation.txt
│   │   │   ├── grammar.txt
│   │   │   └── nmm.txt
│   │   └── study_materials/            # Study resources
│   │       ├── consent_forms/
│   │       ├── task_instructions/
│   │       └── questionnaires/
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                 # Test fixtures
│   │   ├── unit/
│   │   │   ├── __init__.py
│   │   │   ├── test_translation.py
│   │   │   ├── test_animation.py
│   │   │   └── test_gloss.py
│   │   ├── integration/
│   │   │   ├── __init__.py
│   │   │   ├── test_api.py
│   │   │   └── test_pipeline.py
│   │   └── e2e/
│   │       ├── __init__.py
│   │       └── test_workflow.py
│   │
│   ├── scripts/
│   │   ├── seed_gloss_db.py            # Seed gloss database
│   │   ├── export_animations.py        # Export animation data
│   │   └── run_study.py                # Run user study
│   │
│   ├── alembic/                        # Database migrations
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── dev.txt
│   │   └── prod.txt
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── ml/
│   ├── models/
│   │   ├── gloss_predictor.py          # Gloss prediction model
│   │   ├── animation_generator.py      # Animation generation
│   │   └── handshape_classifier.py     # Handshape classification
│   │
│   ├── training/
│   │   ├── train_gloss.py              # Train gloss model
│   │   ├── train_animation.py          # Train animation model
│   │   └── data_loader.py              # Data loading
│   │
│   ├── data/
│   │   ├── asllvd/                     # ASLLVD dataset
│   │   ├── wlasl/                      # WLASL dataset
│   │   └── processed/                  # Processed data
│   │
│   └── notebooks/
│       ├── data_exploration.ipynb
│       └── model_evaluation.ipynb
│
├── tools/
│   ├── animation_editor/               # Animation editing tool
│   ├── gloss_manager/                  # Gloss database manager
│   └── study_admin/                    # Study administration
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── Makefile
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

---

## 8. Implementation Phases

### 8.1 Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION PHASES TIMELINE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: Basic Prototype (Weeks 1-6)                                  │
│  ════════════════════════════════════                                  │
│  ├── Week 1-2: Project Setup & Infrastructure                          │
│  │   ├── Initialize frontend (React + Three.js)                        │
│  │   ├── Initialize backend (FastAPI)                                  │
│  │   ├── Setup development environment                                 │
│  │   └── Basic CI/CD pipeline                                         │
│  │                                                                      │
│  ├── Week 3-4: Avatar & Basic Animation                                │
│  │   ├── Integrate Ready Player Me avatar                              │
│  │   ├── Implement basic skeletal animation                            │
│  │   ├── Create 10 basic ASL signs                                    │
│  │   └── Basic animation playback                                     │
│  │                                                                      │
│  └── Week 5-6: Text Input & Simple Translation                         │
│      ├── Text input interface                                          │
│      ├── Rule-based English→ASL gloss                                  │
│      ├── Basic sign sequence playback                                  │
│      └── Initial testing                                               │
│                                                                         │
│  Phase 2: Voice Input + LLM Integration (Weeks 7-14)                   │
│  ═══════════════════════════════════════════════════                   │
│  ├── Week 7-8: Voice Input                                             │
│  │   ├── Web Speech API integration                                    │
│  │   ├── Whisper API for accuracy                                      │
│  │   ├── Voice activity detection                                      │
│  │   └── Real-time transcription                                       │
│  │                                                                      │
│  ├── Week 9-10: LLM Translation                                        │
│  │   ├── GPT-4/Claude API integration                                  │
│  │   ├── Prompt engineering for ASL gloss                              │
│  │   ├── ASL grammar transformation                                    │
│  │   └── Non-manual marker generation                                  │
│  │                                                                      │
│  └── Week 11-14: Integration & Polish                                  │
│      ├── End-to-end pipeline                                           │
│      ├── Animation blending system                                     │
│      ├── 50+ ASL signs database                                        │
│      └── Performance optimization                                      │
│                                                                         │
│  Phase 3: Two-Hand Modeling Refinement (Weeks 15-22)                   │
│  ═══════════════════════════════════════════════════                   │
│  ├── Week 15-17: Hand Independence                                     │
│  │   ├── Separate hand controllers                                     │
│  │   ├── Individual finger IK                                          │
│  │   ├── Handshape classification system                               │
│  │   └── 26 handshapes (ASL alphabet)                                  │
│  │                                                                      │
│  ├── Week 18-19: Collision Avoidance                                   │
│  │   ├── Bounding sphere collision detection                           │
│  │   ├── Penetration resolution                                        │
│  │   ├── Hand priority system                                          │
│  │   └── Physics-based hand interaction                                │
│  │                                                                      │
│  └── Week 20-22: Synchronization & Polish                              │
│      ├── Temporal synchronization                                      │
│      ├── Spatial alignment                                             │
│      ├── Smooth transitions                                            │
│      └── 100+ ASL signs database                                       │
│                                                                         │
│  Phase 4: User Study with Deaf Community (Weeks 23-30)                 │
│  ═══════════════════════════════════════════════════                   │
│  ├── Week 23-24: Study Preparation                                     │
│  │   ├── IRB approval                                                  │
│  │   ├── Community partnership                                         │
│  │   ├── Study protocol finalization                                   │
│  │   └── Material preparation                                          │
│  │                                                                      │
│  ├── Week 25-27: Pilot Study                                           │
│  │   ├── 5-10 participants                                             │
│  │   ├── Protocol refinement                                           │
│  │   ├── Technical issue resolution                                    │
│  │   └── Feedback incorporation                                        │
│  │                                                                      │
│  └── Week 28-30: Main Study                                            │
│      ├── 30-50 participants                                            │
│      ├── Data collection                                               │
│      ├── Analysis                                                      │
│      └── Paper writing                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Phase 1: Basic Prototype

#### Milestones

| Milestone | Deliverable | Success Criteria |
|-----------|-------------|------------------|
| M1.1 | Project scaffolding | All repos created, CI/CD running |
| M1.2 | Avatar rendering | 3D avatar visible in browser |
| M1.3 | Basic animation | 5 signs animate correctly |
| M1.4 | Text input | Text input triggers animation |
| M1.5 | Rule-based translation | English→ASL gloss working |

#### Technical Tasks

```yaml
phase_1_tasks:
  setup:
    - task: "Initialize React + TypeScript project"
      priority: high
      estimate: 2 days
      
    - task: "Setup Three.js with React Three Fiber"
      priority: high
      estimate: 2 days
      
    - task: "Initialize FastAPI backend"
      priority: high
      estimate: 1 day
      
    - task: "Setup Docker development environment"
      priority: medium
      estimate: 1 day
      
    - task: "Configure CI/CD pipeline"
      priority: medium
      estimate: 1 day

  avatar:
    - task: "Integrate Ready Player Me avatar"
      priority: high
      estimate: 3 days
      
    - task: "Setup skeletal animation system"
      priority: high
      estimate: 3 days
      
    - task: "Implement basic hand rig"
      priority: high
      estimate: 4 days

  animation:
    - task: "Create HELLO sign animation"
      priority: high
      estimate: 2 days
      
    - task: "Create basic sign animations (10 signs)"
      priority: high
      estimate: 5 days
      
    - task: "Implement animation playback system"
      priority: high
      estimate: 3 days

  translation:
    - task: "Build text input component"
      priority: high
      estimate: 2 days
      
    - task: "Implement rule-based gloss converter"
      priority: high
      estimate: 3 days
      
    - task: "Create gloss-to-animation mapper"
      priority: high
      estimate: 3 days
```

### 8.3 Phase 2: Voice Input + LLM Integration

#### Milestones

| Milestone | Deliverable | Success Criteria |
|-----------|-------------|------------------|
| M2.1 | Voice input | Speech recognized with >90% accuracy |
| M2.2 | LLM translation | English→ASL gloss with >80% accuracy |
| M2.3 | NMM generation | Facial expressions generated |
| M2.4 | Animation blending | Smooth transitions between signs |
| M2.5 | 50+ signs | Expanded sign database |

#### LLM Integration Architecture

```python
# LLM Service Architecture

class LLMTranslationService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.prompt_manager = PromptManager()
        self.cache = RedisCache()
        
    async def translate_to_gloss(
        self, 
        english_text: str,
        context: Optional[str] = None,
        register: str = "informal"
    ) -> TranslationResult:
        # Check cache first
        cache_key = self._generate_cache_key(english_text, context, register)
        cached = await self.cache.get(cache_key)
        if cached:
            return TranslationResult.from_cache(cached)
        
        # Prepare prompt
        system_prompt = self.prompt_manager.get_system_prompt()
        user_prompt = self.prompt_manager.format_user_prompt(
            english_text=english_text,
            context=context,
            register=register
        )
        
        # Call LLM
        try:
            response = await self._call_llm(system_prompt, user_prompt)
            result = self._parse_response(response)
            
            # Validate result
            validated = self._validate_gloss_sequence(result)
            
            # Cache result
            await self.cache.set(cache_key, validated.dict(), ttl=3600)
            
            return validated
            
        except Exception as e:
            logger.error(f"LLM translation failed: {e}")
            # Fallback to rule-based
            return await self._fallback_translation(english_text)
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        # Try OpenAI first, fallback to Anthropic
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception:
            response = await self.anthropic_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return response.content[0].text
```

### 8.4 Phase 3: Two-Hand Modeling Refinement

#### Milestones

| Milestone | Deliverable | Success Criteria |
|-----------|-------------|------------------|
| M3.1 | Hand independence | Each hand controlled separately |
| M3.2 | Collision avoidance | No hand penetration |
| M3.3 | Finger IK | Individual finger control |
| M3.4 | 26 handshapes | All ASL alphabet handshapes |
| M3.5 | 100+ signs | Comprehensive sign database |

#### Two-Hand Implementation

```typescript
// Two-Hand Controller Implementation

class TwoHandController {
  private dominantHand: HandController;
  private nonDominantHand: HandController;
  private collisionSystem: CollisionAvoidanceSystem;
  private syncEngine: SynchronizationEngine;
  
  constructor(avatar: Avatar) {
    this.dominantHand = new HandController(
      avatar.skeleton,
      'right',
      { ikChainLength: 5, fingerCount: 5 }
    );
    
    this.nonDominantHand = new HandController(
      avatar.skeleton,
      'left',
      { ikChainLength: 5, fingerCount: 5 }
    );
    
    this.collisionSystem = new CollisionAvoidanceSystem(
      this.dominantHand,
      this.nonDominantHand,
      { minDistance: 0.02, responseForce: 0.1 }
    );
    
    this.syncEngine = new SynchronizationEngine();
  }
  
  async animateSign(sign: ASLSign): Promise<void> {
    // Get hand poses for sign
    const dominantPose = sign.dominantHandPose;
    const nonDominantPose = sign.nonDominantHandPose;
    
    // Synchronize hand movements
    const syncPlan = this.syncEngine.createPlan(
      dominantPose,
      nonDominantPose,
      sign.duration
    );
    
    // Animate with collision avoidance
    await this.animateWithCollisionAvoidance(syncPlan);
  }
  
  private async animateWithCollisionAvoidance(
    plan: SyncPlan
  ): Promise<void> {
    const startTime = performance.now();
    
    while (performance.now() - startTime < plan.duration) {
      const progress = (performance.now() - startTime) / plan.duration;
      
      // Update hand poses
      const dominantTarget = this.interpolatePose(
        plan.dominantStart,
        plan.dominantEnd,
        progress
      );
      
      const nonDominantTarget = this.interpolatePose(
        plan.nonDominantStart,
        plan.nonDominantEnd,
        progress
      );
      
      // Check for collisions
      const collisionResult = this.collisionSystem.checkCollision();
      
      if (collisionResult.hasCollision) {
        // Apply collision resolution
        const adjustments = collisionResult.resolution;
        this.applyAdjustments(adjustments);
      }
      
      // Update hand controllers
      await Promise.all([
        this.dominantHand.moveTo(dominantTarget),
        this.nonDominantHand.moveTo(nonDominantTarget)
      ]);
      
      // Wait for next frame
      await this.waitForNextFrame();
    }
  }
}
```

### 8.5 Phase 4: User Study with Deaf Community

#### Milestones

| Milestone | Deliverable | Success Criteria |
|-----------|-------------|------------------|
| M4.1 | IRB approval | Protocol approved |
| M4.2 | Community partnership | 3+ organizations partnered |
| M4.3 | Pilot study | 5-10 participants completed |
| M4.4 | Main study | 30-50 participants completed |
| M4.5 | Paper submission | JHCI paper submitted |

#### Study Protocol

```yaml
user_study_protocol:
  title: "Evaluation of LLM-Based ASL Virtual Human"
  
  participants:
    target_count: 40
    inclusion_criteria:
      - "Deaf or hard of hearing"
      - "Native or near-native ASL proficiency"
      - "Age 18-65"
      - "Comfortable with technology"
    exclusion_criteria:
      - "Cochlear implant users who don't use ASL"
      - "Non-ASL sign language users"
    
  procedure:
    - step: "Consent"
      duration: "10 minutes"
      description: "Review and sign consent form (in ASL)"
      
    - step: "Pre-study questionnaire"
      duration: "15 minutes"
      description: "Demographics, ASL proficiency, tech experience"
      
    - step: "Training"
      duration: "10 minutes"
      description: "Familiarization with system"
      
    - step: "Task 1: Sentence comprehension"
      duration: "20 minutes"
      description: "Watch 20 signed sentences, identify meaning"
      
    - step: "Task 2: Sign identification"
      duration: "15 minutes"
      description: "Identify 50 individual signs"
      
    - step: "Task 3: Free response"
      duration: "15 minutes"
      description: "Describe 10 signed passages"
      
    - step: "Post-task questionnaires"
      duration: "10 minutes"
      description: "NASA-TLX, SUS"
      
    - step: "Post-study interview"
      duration: "15 minutes"
      description: "Open-ended feedback"
      
    total_duration: "90 minutes"
    
  data_collection:
    - type: "quantitative"
      measures:
        - "Intelligibility scores"
        - "Response times"
        - "Likert scale ratings"
        - "Error rates"
        
    - type: "qualitative"
      measures:
        - "Open-ended responses"
        - "Interview transcripts"
        - "Observation notes"
        
  analysis:
    statistical_tests:
      - "Repeated measures ANOVA"
      - "Paired t-tests"
      - "Friedman test"
      - "Post-hoc Bonferroni"
      
    qualitative_analysis:
      - "Thematic analysis"
      - "Content analysis"
      - "Inter-rater reliability"
```

---

## 9. Key Technical Challenges

### 9.1 Challenge Matrix

| Challenge | Difficulty | Impact | Mitigation Strategy |
|-----------|------------|--------|---------------------|
| ASL Grammar Differences | High | High | LLM-based translation with ASL grammar training |
| Non-Manual Markers | High | High | Facial blend shapes + procedural generation |
| Smooth Transitions | Medium | Medium | Animation blending with easing functions |
| Real-time Performance | Medium | High | LOD, instancing, GPU optimization |
| Two-Hand Coordination | High | Medium | Physics-based collision avoidance |
| Sign Ambiguity | Medium | Medium | Context-aware LLM translation |
| Cultural Appropriateness | High | High | Deaf community involvement |

### 9.2 ASL Grammar Transformation

```python
# ASL Grammar Processor

class ASLGrammarProcessor:
    """
    Transforms English grammar to ASL grammar structure.
    
    ASL Grammar Rules:
    1. Topic-Comment structure
    2. Time markers first
    3. Subject-Object-Verb (SOV) tendency
    4. Spatial referencing for pronouns
    5. Non-manual markers for questions and negation
    """
    
    def transform_to_asl_grammar(self, english_sentence: str) -> ASLGrammarStructure:
        # Parse English sentence
        parsed = self.nlp_parser.parse(english_sentence)
        
        # Extract components
        subject = parsed.subject
        verb = parsed.verb
        obj = parsed.object
        time_marker = parsed.time_expression
        is_question = parsed.is_question
        is_negative = parsed.is_negative
        
        # Transform to ASL structure
        asl_structure = ASLGrammarStructure()
        
        # 1. Add time marker first (if exists)
        if time_marker:
            asl_structure.add_time_marker(time_marker)
        
        # 2. Add topic (subject or object, depending on emphasis)
        if self.is_topic(parsed):
            asl_structure.add_topic(subject)
        
        # 3. Add comment (remaining elements)
        asl_structure.add_comment(verb)
        if obj:
            asl_structure.add_object(obj)
        
        # 4. Add non-manual markers
        if is_question:
            if parsed.question_type == "yes_no":
                asl_structure.add_nmm("raised_eyebrows")
            else:
                asl_structure.add_nmm("furrowed_brows")
        
        if is_negative:
            asl_structure.add_nmm("head_shake")
        
        return asl_structure
    
    def is_topic(self, parsed: ParsedSentence) -> bool:
        """Determine if subject should be topicalized."""
        # Topics are used for emphasis or contrast
        return (
            parsed.has_contrast or
            parsed.is_relative_clause or
            parsed.subject_is_emphasized
        )
```

### 9.3 Non-Manual Marker System

```typescript
// Non-Manual Marker (NMM) Generation System

interface NonManualMarker {
  type: NMMType;
  intensity: number; // 0-1
  timing: {
    start: number; // ms from sign start
    duration: number; // ms
    easing: EasingFunction;
  };
}

enum NMMType {
  // Eyebrows
  RAISED_EYEBROWS = 'raised_eyebrows',
  FURROWED_BROWS = 'furrowed_brows',
  ONE_RAISED_BROW = 'one_raised_brow',
  
  // Eyes
  WIDE_EYES = 'wide_eyes',
  SQUINTED_EYES = 'squinted_eyes',
  EYE_GAZE_LEFT = 'eye_gaze_left',
  EYE_GAZE_RIGHT = 'eye_gaze_right',
  EYE_GAZE_UP = 'eye_gaze_up',
  EYE_GAZE_DOWN = 'eye_gaze_down',
  
  // Mouth
  MOUTH_OPEN = 'mouth_open',
  MOUTH_CLOSED = 'mouth_closed',
  LIPS_PUCKERED = 'lips_puckered',
  LIPS_SPREAD = 'lips_spread',
  TONGUE_OUT = 'tongue_out',
  TEETH_ON_LIP = 'teeth_on_lip',
  
  // Head
  HEAD_NOD = 'head_nod',
  HEAD_SHAKE = 'head_shake',
  HEAD_TILT = 'head_tilt',
  HEAD_BACK = 'head_back',
  
  // Shoulders
  SHOULDER_RAISE = 'shoulder_raise',
  SHOULDER_SHRUG = 'shoulder_shrug',
  
  // Body
  BODY_LEAN_FORWARD = 'body_lean_forward',
  BODY_LEAN_BACK = 'body_lean_back'
}

class NMMGenerator {
  private blendShapeController: BlendShapeController;
  
  generateNMMs(
    glossSequence: GlossSign[],
    context: TranslationContext
  ): NonManualMarker[] {
    const nmms: NonManualMarker[] = [];
    
    for (let i = 0; i < glossSequence.length; i++) {
      const sign = glossSequence[i];
      
      // Question markers
      if (context.isQuestion) {
        if (context.questionType === 'yes_no') {
          nmms.push({
            type: NMMType.RAISED_EYEBROWS,
            intensity: 0.7,
            timing: {
              start: sign.startTime,
              duration: sign.duration,
              easing: 'ease-in-out'
            }
          });
        } else {
          nmms.push({
            type: NMMType.FURROWED_BROWS,
            intensity: 0.6,
            timing: {
              start: sign.startTime,
              duration: sign.duration,
              easing: 'ease-in-out'
            }
          });
        }
      }
      
      // Negation markers
      if (context.isNegative) {
        nmms.push({
          type: NMMType.HEAD_SHAKE,
          intensity: 0.5,
          timing: {
            start: sign.startTime,
            duration: sign.duration,
            easing: 'linear'
          }
        });
      }
      
      // Mouth morphemes (specific to signs)
      const mouthMorpheme = this.getMouthMorpheme(sign.gloss);
      if (mouthMorpheme) {
        nmms.push(mouthMorpheme);
      }
    }
    
    return nmms;
  }
  
  applyNMMs(nmms: NonManualMarker[], currentTime: number): void {
    for (const nmm of nmms) {
      if (currentTime >= nmm.timing.start && 
          currentTime <= nmm.timing.start + nmm.timing.duration) {
        const progress = (currentTime - nmm.timing.start) / nmm.timing.duration;
        const easedProgress = this.applyEasing(progress, nmm.timing.easing);
        const intensity = nmm.intensity * easedProgress;
        
        this.blendShapeController.setBlendShape(nmm.type, intensity);
      }
    }
  }
}
```

### 9.4 Performance Optimization

```typescript
// Performance Optimization Strategies

class PerformanceOptimizer {
  // Level of Detail (LOD) for avatar
  setupLOD(avatar: Avatar): void {
    const lod = new THREE.LOD();
    
    // High detail (close up)
    lod.addLevel(avatar.highDetailModel, 0);
    
    // Medium detail (mid distance)
    lod.addLevel(avatar.mediumDetailModel, 5);
    
    // Low detail (far away)
    lod.addLevel(avatar.lowDetailModel, 15);
    
    avatar.model = lod;
  }
  
  // Animation instancing for multiple avatars
  setupInstancing(avatars: Avatar[]): void {
    const geometry = avatars[0].geometry;
    const material = avatars[0].material;
    
    const instancedMesh = new THREE.InstancedMesh(
      geometry,
      material,
      avatars.length
    );
    
    // Update instance matrices
    avatars.forEach((avatar, index) => {
      instancedMesh.setMatrixAt(index, avatar.matrix);
    });
    
    instancedMesh.instanceMatrix.needsUpdate = true;
  }
  
  // Frustum culling
  setupFrustumCulling(scene: THREE.Scene): void {
    const frustum = new THREE.Frustum();
    const camera = scene.camera;
    
    scene.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.frustumCulled = true;
      }
    });
  }
  
  // Animation compression
  compressAnimation(animation: AnimationClip): AnimationClip {
    // Remove redundant keyframes
    const optimized = this.removeRedundantKeyframes(animation);
    
    // Quantize values
    const quantized = this.quantizeKeyframes(optimized, 16);
    
    // Compress using Draco
    const compressed = this.dracoCompress(quantized);
    
    return compressed;
  }
  
  // GPU-based skinning
  setupGPUSkinning(mesh: THREE.SkinnedMesh): void {
    mesh.material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        '#include <skinning_pars_vertex>',
        `
        #ifdef USE_SKINNING
          uniform mat4 boneMatrices[MAX_BONES];
          
          vec4 skinVertex(vec4 vertex, int boneIndex, float weight) {
            return boneMatrices[boneIndex] * vertex * weight;
          }
        #endif
        `
      );
    };
  }
}
```

---

## 10. Evaluation Metrics

### 10.1 Metrics Framework

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    EVALUATION METRICS FRAMEWORK                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PRIMARY METRICS                               │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │ Intelligibility│  │ Naturalness  │  │ User          │       │   │
│  │  │ Score         │  │ Rating       │  │ Satisfaction  │       │   │
│  │  │               │  │              │  │               │       │   │
│  │  │ Target: >80%  │  │ Target: >4/7 │  │ Target: >5/7  │       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    SECONDARY METRICS                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │ Response Time │  │ Error Rate   │  │ Task          │       │   │
│  │  │               │  │              │  │ Completion    │       │   │
│  │  │ Target: <2s   │  │ Target: <10% │  │ Target: >90%  │       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    TECHNICAL METRICS                             │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │   │
│  │  │ FPS           │  │ Latency      │  │ Memory Usage  │       │   │
│  │  │               │  │              │  │               │       │   │
│  │  │ Target: >30   │  │ Target: <100ms│ │ Target: <500MB│       │   │
│  │  └───────────────┘  └───────────────┘  └───────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 Metric Definitions

```python
# Evaluation Metrics Implementation

class EvaluationMetrics:
    """Comprehensive evaluation metrics for ASL Virtual Human."""
    
    def calculate_intelligibility(
        self,
        responses: List[UserResponse],
        ground_truth: List[str]
    ) -> float:
        """
        Calculate intelligibility score.
        
        Intelligibility = (Correct identifications / Total items) * 100
        
        A response is "correct" if it matches the ground truth meaning,
        even if the exact wording differs.
        """
        correct = 0
        total = len(responses)
        
        for response, truth in zip(responses, ground_truth):
            if self.is_semantically_equivalent(response.answer, truth):
                correct += 1
        
        return (correct / total) * 100
    
    def calculate_naturalness(
        self,
        ratings: List[int]
    ) -> Dict[str, float]:
        """
        Calculate naturalness statistics.
        
        Rating scale: 1 (Very Unnatural) to 7 (Very Natural)
        """
        return {
            'mean': np.mean(ratings),
            'median': np.median(ratings),
            'std': np.std(ratings),
            'min': np.min(ratings),
            'max': np.max(ratings),
            'ci_95': self.confidence_interval(ratings, 0.95)
        }
    
    def calculate_response_time(
        self,
        timestamps: List[Tuple[float, float]]
    ) -> Dict[str, float]:
        """
        Calculate response time statistics.
        
        Response time = Time of user response - Time animation ended
        """
        response_times = [end - start for start, end in timestamps]
        
        return {
            'mean_ms': np.mean(response_times),
            'median_ms': np.median(response_times),
            'p95_ms': np.percentile(response_times, 95),
            'p99_ms': np.percentile(response_times, 99)
        }
    
    def calculate_user_satisfaction(
        self,
        survey_responses: Dict[str, List[int]]
    ) -> Dict[str, float]:
        """
        Calculate user satisfaction from survey responses.
        
        Includes:
        - Overall satisfaction
        - Ease of use
        - Usefulness
        - Likelihood to recommend
        """
        results = {}
        
        for question, ratings in survey_responses.items():
            results[question] = {
                'mean': np.mean(ratings),
                'std': np.std(ratings)
            }
        
        # Calculate System Usability Scale (SUS) score
        results['sus_score'] = self.calculate_sus(
            survey_responses.get('sus_questions', [])
        )
        
        return results
    
    def calculate_sus(self, responses: List[int]) -> float:
        """
        Calculate System Usability Scale (SUS) score.
        
        SUS = 2.5 * (sum of adjusted scores)
        Range: 0-100
        """
        if len(responses) != 10:
            raise ValueError("SUS requires exactly 10 responses")
        
        # Odd items: subtract 1
        # Even items: subtract from 5
        adjusted = []
        for i, score in enumerate(responses):
            if i % 2 == 0:  # Odd items (0-indexed)
                adjusted.append(score - 1)
            else:  # Even items
                adjusted.append(5 - score)
        
        return 2.5 * sum(adjusted)
    
    def calculate_task_completion_rate(
        self,
        tasks: List[TaskResult]
    ) -> float:
        """
        Calculate task completion rate.
        
        Task completion = (Completed tasks / Total tasks) * 100
        """
        completed = sum(1 for task in tasks if task.completed)
        return (completed / len(tasks)) * 100
    
    def calculate_error_rate(
        self,
        errors: List[Error],
        total_attempts: int
    ) -> Dict[str, float]:
        """
        Calculate error rates by category.
        """
        error_counts = {}
        for error in errors:
            category = error.category
            error_counts[category] = error_counts.get(category, 0) + 1
        
        return {
            'total_error_rate': len(errors) / total_attempts,
            'by_category': {
                cat: count / total_attempts 
                for cat, count in error_counts.items()
            }
        }
```

### 10.3 Statistical Analysis

```python
# Statistical Analysis for User Study

class StatisticalAnalyzer:
    """Statistical analysis for user study data."""
    
    def analyze_within_subjects(
        self,
        data: pd.DataFrame,
        dependent_var: str,
        independent_var: str,
        subject_var: str
    ) -> Dict[str, Any]:
        """
        Perform within-subjects analysis.
        
        Uses repeated measures ANOVA with post-hoc tests.
        """
        # Check assumptions
        assumptions = self.check_assumptions(data, dependent_var)
        
        if assumptions['normality'] and assumptions['sphericity']:
            # Repeated measures ANOVA
            anova_result = pg.rm_anova(
                data=data,
                dv=dependent_var,
                within=independent_var,
                subject=subject_var,
                detailed=True
            )
            
            # Post-hoc pairwise comparisons (Bonferroni corrected)
            posthoc = pg.pairwise_tests(
                data=data,
                dv=dependent_var,
                within=independent_var,
                subject=subject_var,
                padjust='bonf'
            )
            
            # Effect size (partial eta squared)
            effect_size = anova_result['p-unc'][0]
            
        else:
            # Non-parametric alternative: Friedman test
            anova_result = pg.friedman(
                data=data,
                dv=dependent_var,
                within=independent_var,
                subject=subject_var
            )
            
            # Post-hoc: Wilcoxon signed-rank tests
            posthoc = pg.pairwise_tests(
                data=data,
                dv=dependent_var,
                within=independent_var,
                subject=subject_var,
                parametric=False,
                padjust='bonf'
            )
            
            effect_size = None
        
        return {
            'anova': anova_result,
            'posthoc': posthoc,
            'effect_size': effect_size,
            'assumptions': assumptions
        }
    
    def check_assumptions(
        self,
        data: pd.DataFrame,
        dependent_var: str
    ) -> Dict[str, bool]:
        """Check statistical assumptions."""
        
        # Normality (Shapiro-Wilk test)
        normality = pg.normality(data[dependent_var])['normal'].all()
        
        # Sphericity (Mauchly's test)
        # Note: Only applicable for >2 levels
        sphericity = True  # Assume met if 2 levels
        
        return {
            'normality': normality,
            'sphericity': sphericity
        }
    
    def calculate_confidence_interval(
        self,
        data: List[float],
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval."""
        n = len(data)
        mean = np.mean(data)
        se = stats.sem(data)
        
        ci = stats.t.interval(
            confidence,
            n - 1,
            loc=mean,
            scale=se
        )
        
        return ci
    
    def effect_size_cohens_d(
        self,
        group1: List[float],
        group2: List[float]
    ) -> float:
        """Calculate Cohen's d effect size."""
        n1, n2 = len(group1), len(group2)
        var1, var2 = np.var(group1, ddof=1), np.var(group2, ddof=1)
        
        # Pooled standard deviation
        pooled_se = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        # Cohen's d
        d = (np.mean(group1) - np.mean(group2)) / pooled_se
        
        return d
```

---

## 11. API Specifications

### 11.1 REST API Endpoints

```yaml
# OpenAPI Specification (Partial)

openapi: 3.0.0
info:
  title: ASL Virtual Human API
  version: 1.0.0
  description: API for ASL Virtual Human translation and animation

servers:
  - url: http://localhost:8000/api/v1
    description: Development server
  - url: https://api.asl-virtual-human.com/v1
    description: Production server

paths:
  /translation/text:
    post:
      summary: Translate English text to ASL gloss
      tags: [Translation]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                text:
                  type: string
                  example: "Hello, my name is John"
                context:
                  type: string
                  example: "greeting"
                register:
                  type: string
                  enum: [formal, informal]
                  default: informal
      responses:
        200:
          description: Translation successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TranslationResult'
        400:
          description: Invalid input
        500:
          description: Translation failed

  /translation/voice:
    post:
      summary: Translate voice input to ASL gloss
      tags: [Translation]
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                audio:
                  type: string
                  format: binary
                language:
                  type: string
                  default: en-US
      responses:
        200:
          description: Translation successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/TranslationResult'

  /animation/play:
    post:
      summary: Play ASL animation sequence
      tags: [Animation]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                gloss_sequence:
                  type: array
                  items:
                    type: string
                  example: ["HELLO", "NAME", "J-O-H-N"]
                speed:
                  type: number
                  default: 1.0
                loop:
                  type: boolean
                  default: false
      responses:
        200:
          description: Animation started
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnimationResponse'

  /animation/status:
    get:
      summary: Get animation playback status
      tags: [Animation]
      responses:
        200:
          description: Current animation status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnimationStatus'

  /gloss/search:
    get:
      summary: Search ASL gloss database
      tags: [Gloss]
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
        - name: limit
          in: query
          schema:
            type: integer
            default: 10
      responses:
        200:
          description: Search results
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/GlossEntry'

  /study/session:
    post:
      summary: Create a new study session
      tags: [Study]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StudySession'
      responses:
        201:
          description: Session created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/StudySessionResponse'

  /study/feedback:
    post:
      summary: Submit study feedback
      tags: [Study]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/StudyFeedback'
      responses:
        200:
          description: Feedback submitted

components:
  schemas:
    TranslationResult:
      type: object
      properties:
        gloss_sequence:
          type: array
          items:
            type: string
        non_manual_markers:
          type: object
        spatial_references:
          type: object
        confidence:
          type: number
        processing_time_ms:
          type: number

    AnimationResponse:
      type: object
      properties:
        animation_id:
          type: string
        status:
          type: string
          enum: [playing, paused, completed, error]
        duration_ms:
          type: number

    AnimationStatus:
      type: object
      properties:
        current_animation:
          type: string
        progress:
          type: number
        fps:
          type: number

    GlossEntry:
      type: object
      properties:
        gloss:
          type: string
        english:
          type: array
          items:
            type: string
        animation_url:
          type: string
        difficulty:
          type: string

    StudySession:
      type: object
      properties:
        participant_id:
          type: string
        condition:
          type: string
        tasks:
          type: array
          items:
            type: string

    StudySessionResponse:
      type: object
      properties:
        session_id:
          type: string
        status:
          type: string
        created_at:
          type: string
          format: date-time

    StudyFeedback:
      type: object
      properties:
        session_id:
          type: string
        task_id:
          type: string
        ratings:
          type: object
        comments:
          type: string
```

### 11.2 WebSocket Protocol

```typescript
// WebSocket Protocol for Real-time Communication

interface WebSocketMessage {
  type: MessageType;
  payload: any;
  timestamp: number;
  id: string;
}

enum MessageType {
  // Client → Server
  TRANSLATE_TEXT = 'translate_text',
  TRANSLATE_VOICE = 'translate_voice',
  PLAY_ANIMATION = 'play_animation',
  PAUSE_ANIMATION = 'pause_animation',
  STOP_ANIMATION = 'stop_animation',
  UPDATE_SPEED = 'update_speed',
  SUBMIT_FEEDBACK = 'submit_feedback',
  
  // Server → Client
  TRANSLATION_RESULT = 'translation_result',
  ANIMATION_UPDATE = 'animation_update',
  ANIMATION_COMPLETE = 'animation_complete',
  ERROR = 'error',
  HEARTBEAT = 'heartbeat'
}

// WebSocket Client Implementation
class ASLWebSocketClient {
  private ws: WebSocket;
  private messageQueue: Map<string, Promise<any>> = new Map();
  
  constructor(url: string) {
    this.ws = new WebSocket(url);
    this.setupHandlers();
  }
  
  private setupHandlers(): void {
    this.ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.handleMessage(message);
    };
    
    this.ws.onclose = () => {
      // Reconnect logic
      setTimeout(() => this.reconnect(), 1000);
    };
  }
  
  async translateText(text: string): Promise<TranslationResult> {
    return this.send({
      type: MessageType.TRANSLATE_TEXT,
      payload: { text },
      timestamp: Date.now(),
      id: this.generateId()
    });
  }
  
  async playAnimation(glossSequence: string[]): Promise<void> {
    return this.send({
      type: MessageType.PLAY_ANIMATION,
      payload: { gloss_sequence: glossSequence },
      timestamp: Date.now(),
      id: this.generateId()
    });
  }
  
  private send<T>(message: WebSocketMessage): Promise<T> {
    return new Promise((resolve, reject) => {
      this.messageQueue.set(message.id, { resolve, reject });
      this.ws.send(JSON.stringify(message));
      
      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.messageQueue.has(message.id)) {
          this.messageQueue.delete(message.id);
          reject(new Error('Request timeout'));
        }
      }, 30000);
    });
  }
  
  private handleMessage(message: WebSocketMessage): void {
    const pending = this.messageQueue.get(message.id);
    if (pending) {
      this.messageQueue.delete(message.id);
      
      if (message.type === MessageType.ERROR) {
        pending.reject(new Error(message.payload.message));
      } else {
        pending.resolve(message.payload);
      }
    }
    
    // Handle streaming updates
    if (message.type === MessageType.ANIMATION_UPDATE) {
      this.onAnimationUpdate(message.payload);
    }
  }
}
```

---

## 12. Performance Requirements

### 12.1 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Frame Rate** | ≥30 FPS (60 FPS preferred) | During animation playback |
| **Initial Load** | <3 seconds | Time to interactive |
| **Translation Latency** | <2 seconds | Text to gloss result |
| **Voice Recognition** | <500ms | Speech to text |
| **Animation Start** | <100ms | From gloss to animation start |
| **Memory Usage** | <500MB | Browser memory |
| **Bundle Size** | <5MB | Initial JavaScript bundle |
| **Avatar Load** | <2 seconds | 3D model load time |

### 12.2 Performance Monitoring

```typescript
// Performance Monitoring System

class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();
  
  // Track translation latency
  trackTranslationLatency(startTime: number, endTime: number): void {
    const latency = endTime - startTime;
    this.recordMetric('translation_latency', latency);
    
    if (latency > 2000) {
      console.warn(`Translation latency exceeded target: ${latency}ms`);
    }
  }
  
  // Track frame rate
  trackFrameRate(): void {
    let lastTime = performance.now();
    let frames = 0;
    
    const measure = () => {
      frames++;
      const currentTime = performance.now();
      
      if (currentTime - lastTime >= 1000) {
        const fps = frames * 1000 / (currentTime - lastTime);
        this.recordMetric('fps', fps);
        
        if (fps < 30) {
          console.warn(`FPS below target: ${fps}`);
        }
        
        frames = 0;
        lastTime = currentTime;
      }
      
      requestAnimationFrame(measure);
    };
    
    requestAnimationFrame(measure);
  }
  
  // Track memory usage
  trackMemoryUsage(): void {
    if (performance.memory) {
      const memory = performance.memory;
      this.recordMetric('heap_used', memory.usedJSHeapSize);
      this.recordMetric('heap_total', memory.totalJSHeapSize);
      
      if (memory.usedJSHeapSize > 500 * 1024 * 1024) {
        console.warn('Memory usage exceeded 500MB');
      }
    }
  }
  
  // Generate performance report
  generateReport(): PerformanceReport {
    const report: PerformanceReport = {};
    
    for (const [metric, values] of this.metrics) {
      report[metric] = {
        mean: this.mean(values),
        median: this.median(values),
        p95: this.percentile(values, 95),
        p99: this.percentile(values, 99),
        min: Math.min(...values),
        max: Math.max(...values)
      };
    }
    
    return report;
  }
  
  private recordMetric(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    this.metrics.get(name)!.push(value);
  }
  
  private mean(values: number[]): number {
    return values.reduce((a, b) => a + b, 0) / values.length;
  }
  
  private median(values: number[]): number {
    const sorted = [...values].sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  }
  
  private percentile(values: number[], p: number): number {
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil((p / 100) * sorted.length) - 1;
    return sorted[index];
  }
}
```

---

## 13. Security Considerations

### 13.1 Security Measures

```yaml
security_measures:
  authentication:
    - method: "JWT (JSON Web Tokens)"
      implementation: "FastAPI security"
      token_expiry: "1 hour"
      refresh_token: true
      
  authorization:
    - method: "Role-Based Access Control (RBAC)"
      roles:
        - admin
        - researcher
        - participant
        - viewer
      
  data_protection:
    - encryption_at_rest: "AES-256"
    - encryption_in_transit: "TLS 1.3"
    - pii_handling: "Anonymization + pseudonymization"
    - data_retention: "5 years, then secure deletion"
    
  api_security:
    - rate_limiting: "100 requests/minute"
    - input_validation: "Pydantic models"
    - sql_injection: "Parameterized queries (SQLAlchemy)"
    - xss_prevention: "Content Security Policy"
    - cors: "Whitelist allowed origins"
    
  infrastructure:
    - firewall: "AWS Security Groups"
    - ddos_protection: "AWS Shield"
    - secrets_management: "AWS Secrets Manager"
    - logging: "Audit logs for all actions"
    
  compliance:
    - gdpr: "Data protection impact assessment"
    - hipaa: "If health data involved"
    - irb: "Institutional review board approval"
```

### 13.2 Data Privacy

```python
# Data Privacy Implementation

class DataPrivacyManager:
    """Manages data privacy and anonymization."""
    
    def anonymize_participant_data(
        self,
        participant: Participant
    ) -> AnonymizedParticipant:
        """Anonymize participant data for analysis."""
        return AnonymizedParticipant(
            id=self.generate_pseudonym(participant.id),
            age_group=self.generalize_age(participant.age),
            region=self.generalize_location(participant.location),
            asl_proficiency=participant.asl_proficiency,
            # Exclude: name, email, exact age, address
        )
    
    def generate_pseudonym(self, real_id: str) -> str:
        """Generate consistent pseudonym."""
        hash_input = f"{real_id}{settings.PSEUDONYM_SALT}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    
    def generalize_age(self, age: int) -> str:
        """Generalize age to age group."""
        if age < 25:
            return "18-24"
        elif age < 35:
            return "25-34"
        elif age < 45:
            return "35-44"
        elif age < 55:
            return "45-54"
        elif age < 65:
            return "55-64"
        else:
            return "65+"
    
    def encrypt_pii(self, data: Dict) -> Dict:
        """Encrypt personally identifiable information."""
        pii_fields = ['name', 'email', 'phone', 'address']
        
        encrypted = data.copy()
        for field in pii_fields:
            if field in encrypted:
                encrypted[field] = self.encrypt(encrypted[field])
        
        return encrypted
    
    def handle_data_deletion_request(self, participant_id: str) -> bool:
        """Handle GDPR data deletion request."""
        # Delete all participant data
        deleted = self.db.delete_participant_data(participant_id)
        
        # Log deletion for audit
        self.audit_log.record_deletion(participant_id)
        
        return deleted
```

---

## 14. References

### 14.1 Academic Papers

| # | Citation | Relevance |
|---|----------|-----------|
| 1 | Neidle, C., et al. (2000). "The Syntax of American Sign Language: Functional Categories and Hierarchical Structure." *MIT Press*. | ASL grammar fundamentals |
| 2 | Stokoe, W. C. (1960). "Sign Language Structure." *Studies in Linguistics, Occasional Papers 8*. | ASL linguistic foundation |
| 3 | Brentari, D. (1998). "A Prosodic Model of Sign Language Phonology." *MIT Press*. | ASL phonology |
| 4 | Padden, C. A., & Humphries, T. (1988). "Deaf in America: Voices from a Culture." *Harvard University Press*. | Deaf culture |
| 5 | Valli, C., & Lucas, C. (2000). "Linguistics of American Sign Language." *Gallaudet University Press*. | ASL linguistics |
| 6 | Huenerfauth, M. (2006). "Generating American Sign Language Classifier Predications." *PhD Thesis, University of Pennsylvania*. | ASL generation |
| 7 | Schnepp, J., et al. (2020). "Synthetic Signing Avatars for Deaf Education." *ACM SIGACCESS*. | Signing avatars |
| 8 | Kipp, M., et al. (2011). "Sign Language Generation with Multiple Avatars." *IVA 2011*. | Multi-avatar signing |
| 9 | McDonald, J., et al. (2016). "Automatic Generation of ASL Sentences." *IEEE FG 2016*. | ASL generation |
| 10 | Tornay, S., et al. (2023). "Large Language Models for Sign Language Translation." *ACL 2023*. | LLM for sign language |

### 14.2 Datasets

| Dataset | URL | Size | Content |
|---------|-----|------|---------|
| **ASLLVD** | [bu.edu/asllrp/asllvd](https://www.bu.edu/asllrp/asllvd/) | 3,000+ signs | ASL Lexicon Video Dataset |
| **WLASL** | [dxli94.github.io/wlasl](https://dxli94.github.io/wlasl/) | 2,000 words | Word-Level ASL dataset |
| **MS-ASL** | [Microsoft](https://www.microsoft.com/en-us/research/project/ms-asl/) | 1,000+ signs | Microsoft ASL dataset |
| **How2Sign** | [how2sign.github.io](https://how2sign.github.io/) | 35 hours | Continuous ASL |
| **PHOENIX-2014T** | [i6.informatik.rwth-aachen.de](https://www-i6.informatik.rwth-aachen.de/aslr/) | German SL | Sign language recognition |

### 14.3 Tools & Libraries

| Tool | URL | Purpose |
|------|-----|---------|
| **Three.js** | [threejs.org](https://threejs.org/) | 3D rendering |
| **React Three Fiber** | [docs.pmnd.rs/react-three-fiber](https://docs.pmnd.rs/react-three-fiber/) | React + Three.js |
| **Ready Player Me** | [readyplayer.me](https://readyplayer.me/) | 3D avatars |
| **Mixamo** | [mixamo.com](https://www.mixamo.com/) | Animation library |
| **FastAPI** | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) | Backend framework |
| **OpenAI API** | [platform.openai.com](https://platform.openai.com/) | LLM integration |
| **Anthropic API** | [anthropic.com](https://www.anthropic.com/) | Claude integration |

### 14.4 Related Projects

| Project | Description | Relevance |
|---------|-------------|-----------|
| **SignAll** | Real-time ASL translation | Commercial solution |
| **HandTalk** | Sign language avatar app | Mobile app reference |
| **ASL-LEX** | ASL lexical database | Linguistic resource |
| **OpenPose** | Hand pose estimation | Computer vision |
| **MediaPipe Hands** | Hand tracking | Google's hand tracking |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **ASL** | American Sign Language |
| **Gloss** | Written representation of signs using English words |
| **NMM** | Non-Manual Markers (facial expressions, body movements) |
| **Classifier** | Handshape that represents a category of objects |
| **Dominant Hand** | The primary hand used for signing (usually right) |
| **Non-Dominant Hand** | The secondary hand (usually left) |
| **Handshape** | The configuration of fingers in a sign |
| **Location** | Where a sign is produced in signing space |
| **Movement** | The motion component of a sign |
| **IK** | Inverse Kinematics |
| **LOD** | Level of Detail |
| **FPS** | Frames Per Second |
| **SUS** | System Usability Scale |
| **NASA-TLX** | NASA Task Load Index |

---

## Appendix B: Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-01-XX | ASL Virtual Human Team | Initial architecture document |

---

## Appendix C: Contact Information

| Role | Name | Email |
|------|------|-------|
| Principal Investigator | [PI Name] | pi@university.edu |
| Lead Developer | [Developer Name] | dev@university.edu |
| ASL Consultant | [Consultant Name] | consultant@deaforg.org |
| User Study Coordinator | [Coordinator Name] | study@university.edu |

---

*This document is a living document and will be updated as the project progresses.*
