'use client';

import React, { useState } from 'react';
import { UserEnrichedSelectWidget } from '@/components/workflow-widgets/inputs/UserEnrichedSelectWidget';

export default function TestUserSelectPage() {
  const [singleValue, setSingleValue] = useState<any>(null);
  const [multiValue, setMultiValue] = useState<any>(null);

  return (
    <div className="p-8 max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold mb-8">Test User Select Widget</h1>

      <div className="space-y-4">
        <div className="border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">Single Selection</h2>
          <UserEnrichedSelectWidget
            label="Select User"
            value={singleValue}
            onChange={(value) => {
              console.log('Single selection changed:', value);
              setSingleValue(value);
            }}
            show_all_option={true}
            placeholder="Select a user..."
          />
          <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
            <strong>Value:</strong> {JSON.stringify(singleValue)}
          </div>
        </div>

        <div className="border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">Multiple Selection</h2>
          <UserEnrichedSelectWidget
            label="Select Users"
            value={multiValue}
            onChange={(value) => {
              console.log('Multi selection changed:', value);
              setMultiValue(value);
            }}
            multiple={true}
            show_all_option={true}
            placeholder="Select users..."
          />
          <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
            <strong>Value:</strong> {JSON.stringify(multiValue)}
          </div>
        </div>

        <div className="border rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-4">With Email Filter</h2>
          <UserEnrichedSelectWidget
            label="Select Email Users"
            value={null}
            onChange={(value) => {
              console.log('Email filter selection changed:', value);
            }}
            multiple={true}
            show_all_option={true}
            channel_filter="email"
            placeholder="Select users with email accounts..."
          />
        </div>
      </div>
    </div>
  );
}