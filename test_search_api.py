#!/usr/bin/env python3
"""
Quick test script to verify search functionality on records API
"""
import requests
import json

# Test the search endpoint directly
def test_search_endpoint():
    base_url = "http://demo.localhost:8000"
    
    # First, get pipelines to find a pipeline ID
    print("1. Getting pipelines...")
    try:
        pipelines_response = requests.get(f"{base_url}/api/pipelines/")
        if pipelines_response.status_code == 200:
            pipelines = pipelines_response.json()
            results = pipelines.get('results', pipelines)
            if results:
                pipeline_id = results[0]['id']
                pipeline_name = results[0]['name']
                print(f"✅ Found pipeline: {pipeline_name} (ID: {pipeline_id})")
                
                # Test search without query (should return all records)
                print("2. Testing records without search...")
                records_response = requests.get(f"{base_url}/api/pipelines/{pipeline_id}/records/")
                if records_response.status_code == 200:
                    all_records = records_response.json()
                    all_results = all_records.get('results', all_records)
                    print(f"✅ Found {len(all_results)} total records")
                    
                    if all_results:
                        # Show sample record titles for reference
                        sample_titles = [record.get('title', 'No title') for record in all_results[:5]]
                        print(f"📝 Sample record titles: {sample_titles}")
                        
                        # Test search with query
                        print("3. Testing search with query...")
                        search_query = sample_titles[0].split()[0] if sample_titles[0] else "test"
                        search_response = requests.get(
                            f"{base_url}/api/pipelines/{pipeline_id}/records/",
                            params={"search": search_query}
                        )
                        if search_response.status_code == 200:
                            search_results = search_response.json()
                            search_records = search_results.get('results', search_results)
                            print(f"✅ Search for '{search_query}' returned {len(search_records)} records")
                            
                            if search_records:
                                search_titles = [record.get('title', 'No title') for record in search_records]
                                print(f"📝 Search result titles: {search_titles}")
                            else:
                                print("⚠️  Search returned no results")
                        else:
                            print(f"❌ Search request failed: {search_response.status_code}")
                            print(f"Response: {search_response.text}")
                    else:
                        print("⚠️  No records found in pipeline")
                else:
                    print(f"❌ Records request failed: {records_response.status_code}")
                    print(f"Response: {records_response.text}")
            else:
                print("⚠️  No pipelines found")
        else:
            print(f"❌ Pipelines request failed: {pipelines_response.status_code}")
            print(f"Response: {pipelines_response.text}")
    except Exception as e:
        print(f"❌ Error testing search: {e}")

if __name__ == "__main__":
    test_search_endpoint()