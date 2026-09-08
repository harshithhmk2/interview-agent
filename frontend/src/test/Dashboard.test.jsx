import { describe, test, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import Dashboard from '../components/Dashboard';

describe('Recruiter Dashboard Component Tests', () => {
  test('renders dashboard titles and kpi labels successfully', () => {
    render(<Dashboard onLaunchPortal={() => {}} />);
    
    expect(screen.getByText('Recruiter Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Screened Candidates')).toBeInTheDocument();
    expect(screen.getByText('Active Positions')).toBeInTheDocument();
    expect(screen.getByText('Avg Match Score')).toBeInTheDocument();
  });

  test('slides open the assessment report drawer upon clicking view report', () => {
    render(<Dashboard onLaunchPortal={() => {}} />);
    
    // View report drawer should be hidden initially
    expect(screen.queryByTestId('report-drawer')).not.toBeInTheDocument();

    const viewButtons = screen.getAllByText('View Report');
    fireEvent.click(viewButtons[0]);

    // Drawer should now render
    expect(screen.getByTestId('report-drawer')).toBeInTheDocument();
    expect(screen.getAllByText('Jane Doe').length).toBeGreaterThanOrEqual(1);
  });

  test('switches tabs in the candidate evaluation report drawer', () => {
    render(<Dashboard onLaunchPortal={() => {}} />);
    
    const viewButtons = screen.getAllByText('View Report');
    fireEvent.click(viewButtons[0]);

    // Highlights tab should be active default
    expect(screen.getByText('Matched Strengths')).toBeInTheDocument();
    expect(screen.queryByTestId('skills-radar')).not.toBeInTheDocument();

    // Click on Radar chart tab
    const radarTab = screen.getByText('radar');
    fireEvent.click(radarTab);
    
    expect(screen.getByTestId('skills-radar')).toBeInTheDocument();
    expect(screen.queryByText('Matched Strengths')).not.toBeInTheDocument();

    // Click on Transcript tab
    const transcriptTab = screen.getByText('transcript');
    fireEvent.click(transcriptTab);
    
    expect(screen.getByText('Welcome Jane. Can you describe your experience orchestrating microservices?')).toBeInTheDocument();
  });

  test('supports pagination across voice reports, cv applications, and job descriptions', () => {
    render(<Dashboard onLaunchPortal={() => {}} />);
    
    // Check reports grid is present
    expect(screen.getByTestId('reports-grid')).toBeInTheDocument();

    // Switch to CV Applications subtab
    const cvTab = screen.getByText(/CV Applications/i);
    fireEvent.click(cvTab);
    expect(screen.getByTestId('resumes-grid')).toBeInTheDocument();

    // Switch to Job Descriptions subtab
    const jobsTab = screen.getByText(/Job Descriptions/i);
    fireEvent.click(jobsTab);
    expect(screen.getByTestId('jobs-grid')).toBeInTheDocument();
  });
});
