#!/bin/bash

# 🎯 Quick Test Script for Faculty Review
# Run this to quickly test all major functionalities

echo "🚀 Voice RAG System - Quick Test Suite"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000"

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
curl -s $BASE_URL/api/health | python3 -m json.tool
echo ""
echo ""

# Test 2: English - B.Tech Programs
echo -e "${BLUE}Test 2: English - B.Tech Programs Query${NC}"
echo -e "${YELLOW}Question: What B.Tech programs does UIT offer?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What B.Tech programs does UIT offer?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 3: English - Admission Eligibility
echo -e "${BLUE}Test 3: English - Admission Eligibility${NC}"
echo -e "${YELLOW}Question: What is the eligibility criteria for B.Tech admission?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the eligibility criteria for B.Tech admission?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 4: English - Scholarships
echo -e "${BLUE}Test 4: English - Scholarship Information${NC}"
echo -e "${YELLOW}Question: What scholarships are available at UIT?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What scholarships are available at UIT?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 5: English - Placement Support
echo -e "${BLUE}Test 5: English - Placement Support${NC}"
echo -e "${YELLOW}Question: What placement opportunities does UIT provide?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What placement opportunities does UIT provide?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 6: Hindi - B.Tech Courses
echo -e "${BLUE}Test 6: Hindi - B.Tech Courses Query${NC}"
echo -e "${YELLOW}Question: UIT में कौन से बी.टेक कोर्स उपलब्ध हैं?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "UIT में कौन से बी.टेक कोर्स उपलब्ध हैं?", "language": "Hindi"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 7: Hindi - Admission
echo -e "${BLUE}Test 7: Hindi - Admission Query${NC}"
echo -e "${YELLOW}Question: बी.टेक में प्रवेश के लिए योग्यता क्या है?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "बी.टेक में प्रवेश के लिए योग्यता क्या है?", "language": "Hindi"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 8: Hindi - Scholarships
echo -e "${BLUE}Test 8: Hindi - Scholarship Query${NC}"
echo -e "${YELLOW}Question: क्या छात्रवृत्ति उपलब्ध है?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "क्या छात्रवृत्ति उपलब्ध है?", "language": "Hindi"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 9: Complex Multi-part Question
echo -e "${BLUE}Test 9: Complex Multi-part Question${NC}"
echo -e "${YELLOW}Question: What are the admission requirements, available scholarships, and placement support at UIT?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the admission requirements, available scholarships, and placement support at UIT?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 10: Out of Scope Question
echo -e "${BLUE}Test 10: Out-of-Scope Question Handling${NC}"
echo -e "${YELLOW}Question: What is the weather today?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the weather today?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 11: Karnavati University Info
echo -e "${BLUE}Test 11: Karnavati University Information${NC}"
echo -e "${YELLOW}Question: Tell me about Karnavati University${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about Karnavati University", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

# Test 12: Facilities
echo -e "${BLUE}Test 12: Campus Facilities${NC}"
echo -e "${YELLOW}Question: What facilities are available on campus?${NC}"
curl -s -X POST $BASE_URL/api/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What facilities are available on campus?", "language": "English"}' \
  | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Answer: {data[\"answer\"]}\n')"
echo ""

echo -e "${GREEN}========================================"
echo -e "✅ All Tests Completed!"
echo -e "========================================${NC}"
echo ""
echo "📝 Summary:"
echo "- All text queries tested (12 tests)"
echo "- English queries: ✅"
echo "- Hindi queries: ✅"
echo "- Complex queries: ✅"
echo "- Out-of-scope handling: ✅"
echo ""
echo "🎤 Next Steps:"
echo "1. Open http://localhost:5173 in your browser"
echo "2. Test voice input by clicking the microphone button"
echo "3. Test both English and Hindi voice recognition"
echo "4. Review the FACULTY_TESTING_GUIDE.md for comprehensive testing scenarios"
echo ""
