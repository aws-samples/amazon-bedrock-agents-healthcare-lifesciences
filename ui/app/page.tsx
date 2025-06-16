"use client";

import Head from 'next/head';
import Image from 'next/image';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';


export default function Home() {
  const [search, setSearch] = useState('');
  const [agents, setAgents] = useState([]);
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [filter, setFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [hoveredCollaborator, setHoveredCollaborator] = useState(null);
  let previewTimeout = null;

  const isSupervisorType = (a) => a.agentCollaboration === 'SUPERVISOR' || a.agentCollaboration === 'SUPERVISOR_ROUTER';

  const isCheckboxDisabled = (agent) => {
    
    const hasSupervisorSelected = selectedAgents.some(isSupervisorType);
    const isSupervisor = isSupervisorType(agent);
  
    if (hasSupervisorSelected) {
      return !selectedAgents.find(a => a.id === agent.id) && !isSupervisorType(agent);
    }
  
    const hasIndividualsSelected = selectedAgents.length > 0;
    if (hasIndividualsSelected && !isSupervisor) {
      return false; // other individuals still selectable
    }
  
    if (hasIndividualsSelected && isSupervisor) {
      return true; // disable supervisor if individual is selected
    }
  
    return false;
  };
  

  useEffect(() => {
    async function fetchAgents() {
      setIsLoading(true);
      try {
        const res = await fetch('/api/agents');
        const agentData = await res.json();
        setAgents(agentData);
      } catch (err) {
        console.error('Error fetching agents:', err);
      }
      setIsLoading(false);
    }
    fetchAgents();
  }, []);

  const toggleAgentSelection = (agent) => {
    setSelectedAgents((prev) => {
      const isAlreadySelected = prev.find((a) => a.id === agent.id);
      return isAlreadySelected ? prev.filter((a) => a.id !== agent.id) : [...prev, agent];
    });
  };

  const handleCardClick = (e, agent) => {
    if (e.target.type === 'checkbox') return;
    setSelectedAgent(agent);
  };

  const renderAgents = (title, filterFn) => {
    const filtered = agents.filter((agent) =>
      agent.name.toLowerCase().includes(search.toLowerCase()) && filterFn(agent)
    );
    if (filtered.length === 0) return null;

    return (
      <div>
        <h2 className="text-xl font-semibold mb-2 mt-6 text-blue-800">{title}</h2>
        <div className="grid grid-cols-2 gap-6">
          {filtered.map((agent) => (
            <div
            key={agent.id}
            className={`bg-white p-6 shadow-lg rounded-lg flex items-center cursor-pointer transition transform hover:scale-105 hover:shadow-2xl border-2 ${
              isSupervisorType(agent) ? 'border-purple-500' : 'border-gray-300'
            }`}
            onClick={(e) => handleCardClick(e, agent)}
          >
              <input
                  type="checkbox"
                  className="mr-4"
                  checked={selectedAgents.some((a) => a.id === agent.id)}
                  disabled={isCheckboxDisabled(agent)}
                  onChange={(e) => {
                    e.stopPropagation();
                    toggleAgentSelection(agent);
                  }}
                />
              <img src={agent.image} alt="Agent Icon" className="w-20 h-20 mr-6 rounded-full border-2 border-blue-500 shadow-lg" />
              <div>
                <h3 className="font-bold text-lg text-gray-900">{agent.name}</h3>
                <p className="text-sm text-gray-600">{agent.description}</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  {agent.tags?.length ? (
                    agent.tags.map((tag) => (
                      <span key={tag} className="bg-blue-200 text-blue-800 text-xs px-3 py-1 rounded-full shadow-md">{tag}</span>
                    ))
                  ) : (
                    <span className="text-gray-500 text-xs">No tags available</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const LoadingSpinner = () => (
    <div className="flex flex-col justify-center items-center py-10">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-600"></div>
      <p className="text-blue-600 font-semibold">Loading agents...</p>
    </div>
  );

  return (
    <div>
      <Head>
        <title>Healthcare & Life Sciences AI Agents</title>
      </Head>
      <div className="container p-4">
        <div className="flex flex-col items-center mb-4">
          <Image src="/images/aws-logo.svg" alt="AWS Logo" width={150} height={50} className="mb-4" />
          <h1 className="text-2xl font-bold">Healthcare and Life Sciences Agent Catalog</h1>
        </div>

        {/* Filter Bar */}
        <div className="flex gap-3 mb-4">
          {['all', 'collaborator', 'non-collaborator'].map((type) => (
            <span
              key={type}
              onClick={() => setFilter(type)}
              className={`cursor-pointer px-4 py-1 rounded-full border text-sm transition ${
                filter === type ? 'bg-blue-200 border-blue-500 text-blue-700' : 'bg-gray-100 border-gray-300 text-gray-600'
              }`}
            >
              {type === 'all' ? 'All' : type === 'collaborator' ? 'Supervisors' : 'Individual'}
            </span>
          ))}
        </div>

        <input
          type="text"
          className="w-full p-2 border rounded mb-4"
          placeholder="Search for AI Healthcare Agents"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />

        {/* Agents Section */}
        {isLoading ? (
            <LoadingSpinner />
          ) : (
            <>
              {(filter === 'all' || filter === 'collaborator') &&
                renderAgents('Supervisors', isSupervisorType)}

              {(filter === 'all' || filter === 'non-collaborator') &&
                renderAgents('Individual Agents', (a) => a.agentCollaboration === 'DISABLED')}
            </>
          )}


        <div className="mt-6 flex justify-center gap-4">
          {/* <a href="register.html" className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-700">Register New Agent</a> */}
          <a
            href="/chat"
            className={`bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-700 ${
              selectedAgents.length === 0 ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            onClick={(e) => {
              if (selectedAgents.length === 0) {
                e.preventDefault();
                return;
              }
              localStorage.setItem('selectedAgents', JSON.stringify(selectedAgents));
            }}
          >
            Start Chat with Selected
          </a>
        </div>

        {/* Agent Detail Panel */}
        {selectedAgent && (
  <motion.div
    initial={{ x: "100%" }}
    animate={{ x: 0 }}
    exit={{ x: "100%" }}
    transition={{ duration: 0.3 }}
    className="fixed top-0 right-0 w-1/3 bg-white p-6 shadow-2xl h-full overflow-y-auto rounded-l-lg border-l-4 border-blue-500"
  >
    <button className="float-right text-lg font-bold text-gray-600 hover:text-gray-900" onClick={() => setSelectedAgent(null)}>×</button>
    <img src={selectedAgent.image} alt="Agent Icon" className="w-24 h-24 mx-auto mb-4 rounded-full border-4 border-blue-500 shadow-lg" />
    <h2 className="text-2xl font-bold text-center text-gray-900">{selectedAgent.name}</h2>
    <p className="text-center text-gray-600 mb-4">{selectedAgent.description}</p>

    <div className="p-4 bg-gray-100 rounded-lg">
      <h3 className="font-bold text-md text-gray-800">Details</h3>
      <ul className="text-sm text-gray-700 mt-2 space-y-1">
        <li><strong>Agent ID:</strong> {selectedAgent.id}</li>
        <li><strong>ARN:</strong> {selectedAgent.arn}</li>
        <li><strong>Collaboration:</strong> {selectedAgent.agentCollaboration}</li>
        <li><strong>Status:</strong> {selectedAgent.agentStatus}</li>
        <li><strong>Foundation Model:</strong> {selectedAgent.foundationModel}</li>
        <li><strong>Orchestration Type:</strong> {selectedAgent.orchestrationType}</li>
        <li><strong>Instruction:</strong> {selectedAgent.instruction}</li>
        <li><strong>Created At:</strong> {selectedAgent.createdAt}</li>
        <li><strong>Updated At:</strong> {selectedAgent.updatedAt}</li>
      </ul>
    </div>

    {/* 💡 Added Tags Section */}
    <div className="mt-4">
      <h3 className="font-bold text-md text-gray-800">Tags</h3>
      <div className="flex flex-wrap gap-2 mt-2">
        {selectedAgent.tags && selectedAgent.tags.length > 0 ? (
          selectedAgent.tags.map((tag) => (
            <span key={tag} className="bg-blue-300 text-blue-900 text-xs px-3 py-1 rounded-full shadow-md">{tag}</span>
          ))
        ) : (
          <span className="text-gray-500 text-xs">No tags available</span>
        )}
      </div>
    </div>

    {/* Collaborators Section */}
    {Array.isArray(selectedAgent.collaborators) && selectedAgent.collaborators.length > 0 && (
  <div className="mt-6 border-t pt-4">
    <h3 className="font-bold text-md text-gray-800 mb-3">Collaborators</h3>
    <div className="flex flex-wrap gap-4">
      {selectedAgent.collaborators.map((collabName) => {
        const collaboratorAgent = agents.find(a => a.name === collabName);
        if (!collaboratorAgent) return null;

        return (
          <div
            key={collaboratorAgent.id}
            className="flex items-center gap-4 bg-white border border-gray-200 rounded-lg p-3 w-full hover:shadow-md transition-shadow duration-200 cursor-pointer"
            onMouseEnter={() => {
              clearTimeout(previewTimeout);
              setHoveredCollaborator(collaboratorAgent);
            }}
            onMouseLeave={() => {
              previewTimeout = setTimeout(() => setHoveredCollaborator(null), 300);
            }}
          >
            <img
              src={collaboratorAgent.image}
              alt={`${collaboratorAgent.name} Icon`}
              className="w-12 h-12 rounded-full border-2 border-blue-500 shadow"
            />
            <div className="flex flex-col">
              <div className="text-sm font-semibold text-gray-900">{collaboratorAgent.name}</div>
              <div className="text-xs text-gray-600">{collaboratorAgent.description}</div>
              <div className="flex flex-wrap gap-1 mt-1">
                {collaboratorAgent.tags?.length ? (
                  collaboratorAgent.tags.map(tag => (
                    <span
                      key={tag}
                      className="bg-blue-200 text-blue-800 text-[10px] px-2 py-0.5 rounded-full"
                    >
                      {tag}
                    </span>
                  ))
                ) : (
                  <span className="text-gray-400 text-[10px]">No tags</span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  </div>
)}
  

  </motion.div>
  
)}

{hoveredCollaborator && (
  <motion.div
    initial={{ x: "100%", opacity: 0 }}
    animate={{ x: 0, opacity: 1 }}
    exit={{ x: "100%", opacity: 0 }}
    transition={{ duration: 0.3 }}
    onMouseEnter={() => clearTimeout(previewTimeout)}
    onMouseLeave={() => {
      previewTimeout = setTimeout(() => setHoveredCollaborator(null), 300);
    }}
    className="fixed top-0 right-1/3 w-1/3 bg-white p-6 shadow-2xl h-full overflow-y-auto rounded-l-lg border-l-4 border-purple-500 z-50"
  >
    <img src={hoveredCollaborator.image} alt="Collaborator Icon" className="w-20 h-20 mx-auto mb-4 rounded-full border-4 border-purple-500 shadow-lg" />
    <h2 className="text-xl font-bold text-center text-gray-900">{hoveredCollaborator.name}</h2>
    <p className="text-center text-gray-600 mb-4">{hoveredCollaborator.description}</p>

    <div className="p-4 bg-gray-100 rounded-lg">
      <h3 className="font-bold text-md text-gray-800">Details</h3>
      <ul className="text-sm text-gray-700 mt-2 space-y-1">
        <li><strong>Agent ID:</strong> {hoveredCollaborator.id}</li>
        <li><strong>ARN:</strong> {hoveredCollaborator.arn}</li>
        <li><strong>Collaboration:</strong> {hoveredCollaborator.agentCollaboration}</li>
        <li><strong>Status:</strong> {hoveredCollaborator.agentStatus}</li>
        <li><strong>Foundation Model:</strong> {hoveredCollaborator.foundationModel}</li>
        <li><strong>Orchestration Type:</strong> {hoveredCollaborator.orchestrationType}</li>
        <li><strong>Instruction:</strong> {hoveredCollaborator.instruction}</li>
        <li><strong>Created At:</strong> {hoveredCollaborator.createdAt}</li>
        <li><strong>Updated At:</strong> {hoveredCollaborator.updatedAt}</li>
      </ul>
    </div>

    <div className="mt-4">
      <h3 className="font-bold text-md text-gray-800">Tags</h3>
      <div className="flex flex-wrap gap-2 mt-2">
        {hoveredCollaborator.tags?.length > 0 ? (
          hoveredCollaborator.tags.map((tag) => (
            <span key={tag} className="bg-purple-200 text-purple-800 text-xs px-3 py-1 rounded-full shadow-md">{tag}</span>
          ))
        ) : (
          <span className="text-gray-500 text-xs">No tags available</span>
        )}
      </div>
    </div>
  </motion.div>
)}



      </div>
    </div>
  );
}
