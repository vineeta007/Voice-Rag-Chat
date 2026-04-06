#!/usr/bin/env python3
"""
Filter RAG chunks to keep only UIT-relevant information
"""
import json

def should_keep_chunk(chunk):
    """Determine if a chunk should be kept for UIT bot"""
    chunk_id = chunk.get('id', '')
    program = chunk.get('program', '')
    category = chunk.get('category', '')
    
    # Always keep UIT-specific entries
    if program in ['ALL_UIT', 'B.Tech', 'B.Tech CSE', 'B.Tech AIML']:
        return True
    
    # For general (ALL) entries, keep only relevant ones
    if program == 'ALL':
        # Keep infrastructure, services, and campus-related entries
        keep_categories = [
            'infrastructure',
            'services',
            'financial_support',
            'location_access',
            'campus_policies',
            'accreditation',
            'institution_identity',
            'placement_statistics',
            'philosophy'
        ]
        
        if category in keep_categories:
            return True
        
        # Keep specific entries by ID
        keep_ids = [
            'ku_recognition',
            'ku_wifi_facility',
            'ku_scholarships',
            'ku_hostel_facilities',
            'ku_hostel_amenities',
            'ku_hostel_mess_food',
            'ku_hostel_rooms',
            'ku_hostel_location_access',
            'ku_sports_facilities',
            'ku_library',
            'ku_location',
            'ku_accessibility',
            'ku_safety',
            'ku_attendance_policy',
            'ku_identity',
            'ku_engineering_offerings'  # This one mentions UIT
        ]
        
        if chunk_id in keep_ids:
            return True
    
    return False

def main():
    # Load original data
    with open('rag_chunks_with_faculty.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Original data: {len(data)} chunks")
    
    # Filter to keep only UIT-relevant chunks
    filtered_data = [chunk for chunk in data if should_keep_chunk(chunk)]
    
    print(f"✅ Filtered data: {len(filtered_data)} chunks")
    print(f"🗑️  Removed: {len(data) - len(filtered_data)} chunks")
    
    # Update the ku_academic_fields entry to focus on UIT
    for chunk in filtered_data:
        if chunk['id'] == 'ku_academic_fields':
            chunk['content'] = "Karnavati University offers engineering programs through Unitedworld Institute of Technology (UIT), including B.Tech in Computer Science, AI & ML, Data Science, Cyber Security, and Electronics & Communication Engineering."
            chunk['keywords'] = [
                "programmes",
                "fields",
                "engineering",
                "UIT",
                "B.Tech",
                "offerings",
                "courses"
            ]
    
    # Save filtered data
    with open('rag_chunks_with_faculty.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved filtered data to rag_chunks_with_faculty.json")
    
    # Show category breakdown
    categories = {}
    for chunk in filtered_data:
        cat = chunk.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n📊 Category breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count}")

if __name__ == '__main__':
    main()
